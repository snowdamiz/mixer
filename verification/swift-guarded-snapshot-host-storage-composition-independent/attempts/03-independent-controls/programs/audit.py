"""Independent frozen-data audit. No compiler, fixture, native or product dispatch.

The candidate model is imported only by hostile_controls.py as the test subject.
This module independently binds source/custody, layout observations and rosters.
"""
from pathlib import Path
import collections, gzip, hashlib, json, re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
V = ROOT / 'verification'
CANDIDATE = V / 'swift-guarded-snapshot-host-storage-composition'
SOURCE = '690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'
HOST = '027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2'
CANDIDATE_SEAL = 'ddbd969da4b25240fbc5883e8691905b1b6204fcca47a6a1a9ada4e6a41420a4'
RELEASE = V / 'swift-semantic-adapter-root-review/guarded-snapshot-host-storage-frozen-release.json'
RELEASE_SHA = 'f0062561a5e152f746e25628fd17c0514977fd75483ce448f5b06d29dc49e9ab'

def digest(data): return hashlib.sha256(data).hexdigest()
def canonical(value): return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
def read(path):
    path = Path(path)
    assert path.is_file() and not path.is_symlink() and path.resolve() == path.absolute(), path
    return path.read_bytes()
def js(path): return json.loads(read(path))

def packet(path, expected):
    path = Path(path)
    seal_data = read(path / 'seal.json')
    assert digest(seal_data) == expected, (path, 'seal')
    seal = json.loads(seal_data)
    members = seal['members']
    assert len(members) == seal['member_count'] == len({x['path'] for x in members})
    total = 0
    for row in members:
        relative = Path(row['path'])
        assert not relative.is_absolute() and '..' not in relative.parts
        data = read(path / relative)
        assert (len(data), digest(data)) == (row['bytes'], row['sha256']), (path, relative)
        total += len(data)
    return {'path': str(path.relative_to(ROOT)), 'seal_sha256': expected,
            'member_count': len(members), 'member_bytes': total}

def source_path(relative):
    overlay = V / 'swift-guarded-snapshot-host-composition/overlay/vm' / relative
    return overlay if overlay.exists() else V / 'swift-guarded-snapshot-funding-implementation/source/vm' / relative

def custody():
    assert digest(read(RELEASE)) == RELEASE_SHA
    release = js(RELEASE)
    assert release['acceptance'] is False and release['seal_sha256'] == CANDIDATE_SEAL
    first = packet(CANDIDATE, CANDIDATE_SEAL)
    assert (first['member_count'], first['member_bytes']) == (30, 5567758)
    bindings = js(CANDIDATE / 'input-bindings.json')
    files = []
    for row in bindings['files']:
        data = read(ROOT / row['path'])
        assert (len(data), digest(data)) == (row['bytes'], row['sha256'])
        files.append(row)
    packets = [packet(ROOT / row['path'], row['seal_sha256']) for row in bindings['packets']]
    manifest = js(V / 'swift-guarded-snapshot-host-composition/source-manifest.json')
    assert manifest['member_count'] == 146 and manifest['tree_sha256'] == SOURCE
    assert digest(canonical(manifest['members'])) == SOURCE
    for row in manifest['members']:
        data = read(source_path(row['path']))
        assert (len(data), digest(data)) == (row['bytes'], row['sha256'])
    host = js(V / 'swift-guarded-snapshot-host-composition/host-support-manifest.json')
    assert host['member_count'] == 11 and host['tree_sha256'] == HOST
    assert digest(canonical(host['members'])) == HOST
    for row in host['members']:
        data = read(V / 'swift-real-profile-loader-binding/host' / row['path'])
        assert (len(data), digest(data)) == (row['bytes'], row['sha256'])
    return {'candidate': first, 'root_release_sha256': RELEASE_SHA,
            'input_files': files, 'input_packets': packets,
            'source_members': 146, 'source_tree_sha256': SOURCE,
            'host_members': 11, 'host_tree_sha256': HOST}

def resource_supplement():
    """Only root-released source resource review; no active binary lane reads."""
    acceptance_path = V / 'swift-semantic-adapter-root-review/guarded-snapshot-resource-cost-host-acceptance.json'
    acceptance_sha = '854c90f7824676cec2483571d5de4fce27965758e7e583186fa2361d965a118f'
    assert digest(read(acceptance_path)) == acceptance_sha
    acceptance = js(acceptance_path)
    assert acceptance['source_tree_sha256'] == SOURCE and acceptance['typed_rows'] == 33
    independent = packet(V / 'swift-guarded-snapshot-resource-cost-independent', '649a6005543ea8bc147a70a4fc17a62c455ae9192d1d8d72197a5b86cb711ddc')
    assert (independent['member_count'], independent['member_bytes']) == (62, 2783515)
    assert acceptance['compiled_std_correspondence_complete'] is False
    capacities = js(V / 'swift-guarded-snapshot-resource-cost/capacity-backing-interface.json')
    frontier = capacities['vector_frontiers']
    cache = capacities['cache_index_bytes'] + sum(frontier[x]['max_requested_bytes'] for x in ['Vec<SwiftSlot>','Vec<PinRecord>','Vec<Patch>','Vec<Option<ScanPlan>>'])
    assert cache == 54976 and capacities['cancellation_shared_requested_bytes'] == 24
    assert capacities['storage_ownership_or_alias_discount_selected_here'] is False
    return {'root_acceptance_sha256':acceptance_sha,'independent_packet':independent,
            'source_resource_component_accepted_after_target_freeze':True,
            'target_acceptance_false_is_conservative_historical_status':True,
            'cache_initial_max_requested_bytes':cache,'compiled_std_correspondence_complete':False,
            'no_zero_File_Error_or_destructor_bound_selected':True,
            'binary_lane_read_or_inferred':False}

def type_key(text):
    return re.sub(r'\{closure@.*?/src/', '{closure@<SRC>/', text).replace("'static", "'_")

def qualify(text):
    # MIR aliases are scoped to this exact frozen loader/validator closure.
    modules = {'swift':'experimental::swift', 'metadata':'experimental::metadata',
               'reader':'experimental::reader', 'descriptor':'experimental_wasi::descriptor',
               'retained_profile_loader_v1':'experimental_swift_reactor::retained_profile_loader_v1',
               'control':'experimental_swift_reactor::control'}
    names = {'File':'std::fs::File', 'Error':'std::io::Error', 'Metadata':'std::fs::Metadata',
             'Instant':'std::time::Instant', 'Duration':'std::time::Duration',
             'SwiftControl':'experimental::account::SwiftControl',
             'SwiftDeclaration':'experimental::metadata::SwiftDeclaration',
             'SwiftMetadata':'experimental::metadata::Metadata<experimental::metadata::SwiftDeclaration>',
             'Option':'std::option::Option', 'Result':'std::result::Result', 'Vec':'std::vec::Vec',
             'Ordering':'std::cmp::Ordering', 'BodyState':'experimental::validate::BodyState',
             'ResolveError':'experimental_wasi::descriptor::ResolveError',
             'TryFromIntError':'std::num::TryFromIntError',
             'TryReserveError':'std::collections::TryReserveError'}
    for name in ['Signature','Import','Function','Global','Export','Segment']:
        names[name] = 'experimental::metadata::' + name
    for name in ['FileIdentityV1','BuildView','SessionView','Section','Bytes','Role','Refusal',
                 'SelectedValidatedProfileV1','LoaderFailureV1','LoaderUsageV1',
                 'ReturnedLoaderFilesV1','LoaderOutcomeV1','ProcessObservationV1']:
        names[name] = 'experimental_swift_reactor::retained_profile_loader_v1::' + name
    result = type_key(text)
    for name, replacement in modules.items():
        result = re.sub(r'(?<![\w:])' + name + r'::', lambda m: replacement + '::', result)
    for name, replacement in names.items():
        result = re.sub(r'(?<![\w:])' + name + r'\b', lambda m: replacement, result)
    return result

def layout_catalog():
    data = read(V / 'swift-guarded-snapshot-host-composition-independent/commands/exact146-metadata-mir/stdout.gz')
    assert digest(data) == '1ddc23c6274a1c4f148e9d4a389aa0aeaa070384929280de044f4889a49ec9ec'
    raw = gzip.decompress(data)
    assert digest(raw) == '6c924c8088173db78afb1f648b284df7d8d139b3389bd090a9552df4130cfe7a'
    matches = re.findall(rb'^print-type-size type: `([^`]+)`: (\d+) bytes, alignment: (\d+) bytes$', raw, re.M)
    assert len(matches) == 3072
    table = {}
    def insert(name, size, alignment):
        key = type_key(name); value = (int(size), int(alignment))
        assert key not in table or table[key] == value, ('ambiguous exact type', key)
        table[key] = value
    for name, size, alignment in matches: insert(name.decode(), size, alignment)
    named = js(V / 'swift-guarded-snapshot-source146-callee-storage-layouts/results.json')
    assert named['source_tree_sha256'] == SOURCE and len(named['queries']) == 21
    for row in named['queries']: insert(row['concrete'].replace('crate::', ''), row['size'], row['alignment'])
    closure_dir = V / 'swift-guarded-snapshot-source146-closure-layouts'
    archive = js(closure_dir / 'layout-archive.json')
    closure_data = read(closure_dir / 'compiler.stdout.gz')
    assert digest(closure_data) == archive['archive_sha256']
    closure_raw = gzip.decompress(closure_data)
    assert digest(closure_raw) == archive['raw_sha256']
    closure = js(closure_dir / 'results.json')
    assert closure['production_bodies_unchanged'] and len(closure['closures']) == 6
    for row in closure['closures']:
        assert row['exact_raw_line'].encode() in closure_raw
        match = re.fullmatch(r'print-type-size type: `([^`]+)`: (\d+) bytes, alignment: (\d+) bytes', row['exact_raw_line'])
        assert match and (int(match[2]), int(match[3])) == (row['bytes'], row['alignment'])
        insert(match[1], row['bytes'], row['alignment'])
    return table

PRIMITIVES = {'()':0, '!':0, 'bool':1, 'u8':1, 'i8':1, 'u16':2, 'i16':2,
              'u32':4, 'i32':4, 'u64':8, 'i64':8, 'usize':8, 'isize':8,
              'u128':16, 'i128':16, 'f32':4, 'f64':8}

def concrete_extent(original, table):
    for key in [type_key(original), qualify(original)]:
        if key in table: return table[key][0]
    if original in PRIMITIVES: return PRIMITIVES[original]
    if original.startswith(('&', '*const ', '*mut ')):
        inner = original[1:].removeprefix('mut ').strip() if original[0] == '&' else original.split(' ', 1)[1]
        unsized = inner in ['str', 'std::path::Path', 'std::ffi::OsStr', 'std::ffi::CStr'] or inner.startswith('dyn ') or inner.startswith('[') and ';' not in inner
        return 16 if unsized else 8
    array = re.fullmatch(r'\[(.+); (\d+)\]', original)
    if array:
        element = concrete_extent(array[1], table)
        return None if element is None else element * int(array[2])
    for wrapper in ['std::mem::ManuallyDrop', 'std::mem::MaybeUninit', 'std::mem::MaybeDangling', 'std::option::Option']:
        key = wrapper + '<' + type_key(original) + '>'
        if key in table: return table[key][0]
    return None

def angle_argument(text, marker):
    if marker not in text: return None
    start = text.index(marker) + len(marker); depth = 1
    for i in range(start, len(text)):
        if text[i] == '<': depth += 1
        elif text[i] == '>':
            depth -= 1
            if depth == 0: return text[start:i], text[i+1:]
    raise AssertionError(('unclosed generic argument', text))

def generic_roster(extracted):
    elements = set(); by_method = collections.defaultdict(set); ns = set(); metadata = set()
    for function in extracted['functions'].values():
        for call in function['calls']:
            parsed = angle_argument(call, 'experimental::account::Buffer::<')
            if parsed and parsed[0] != 'T':
                element, tail = parsed
                method = re.match(r'::([A-Za-z_]+)', tail)
                assert method
                elements.add(qualify(element)); by_method[method[1]].add(qualify(element))
            parsed = angle_argument(call, 'retained_profile_loader_v1::Bytes::<')
            if parsed and parsed[0] != 'N': ns.add(int(parsed[0]))
            parsed = angle_argument(call, 'experimental::metadata::read::<')
            if parsed: metadata.add(tuple(qualify(x.strip()) for x in parsed[0].split(',')))
    expected = {'Type','std::option::Option<Type>','experimental::metadata::Signature',
                'experimental::metadata::Import','experimental::metadata::Function',
                'experimental::metadata::Global','experimental::metadata::Export',
                'experimental::metadata::Segment','experimental::validate::Control','u32'}
    assert elements == expected, (sorted(elements - expected), sorted(expected - elements))
    assert ns == {4096, 16384}
    assert metadata == {('experimental::metadata::SwiftDeclaration', 'experimental::account::SwiftControl')}
    return {'elements': sorted(elements), 'by_method': {k:sorted(v) for k,v in sorted(by_method.items())},
            'N': sorted(ns), 'metadata_D_C': [list(x) for x in sorted(metadata)]}

def generic_extent(original, table, roster):
    elements = roster['elements']; key = type_key(original)
    if key == 'T': candidates = elements
    elif key == 'std::option::Option<T>': candidates = ['std::option::Option<' + x + '>' for x in roster['by_method']['pop']]
    elif key == 'std::option::Option<&mut T>': candidates = ['std::option::Option<&mut ' + x + '>' for x in set(roster['by_method']['get_mut'] + roster['by_method']['last_mut'])]
    elif key in ['experimental::account::Buffer<T>', 'std::vec::Vec<T>', "std::slice::Iter<'_, T>", 'std::option::Option<&T>']:
        candidates = [key.replace('T', element) for element in elements]
    elif key == 'D': candidates = [roster['metadata_D_C'][0][0]]
    elif key in ['experimental::metadata::Metadata<D>', 'std::result::Result<experimental::metadata::Metadata<D>, experimental::Failure>']:
        candidates = [key.replace('<D>', '<' + roster['metadata_D_C'][0][0] + '>')]
    elif key == 'experimental_swift_reactor::retained_profile_loader_v1::Bytes<N>':
        candidates = [key.replace('<N>', '<' + str(n) + '>') for n in roster['N']]
    elif key == '[u8; N]': candidates = ['[u8; ' + str(n) + ']' for n in roster['N']]
    else: return None, None
    observations = [concrete_extent(x, table) for x in candidates]
    assert None not in observations, (original, candidates)
    return max(observations), sorted(candidates)

def graph_closure(nodes, start):
    found = set(); pending = [start]
    while pending:
        name = pending.pop()
        assert name in nodes, ('missing callback node', name)
        if name in found: continue
        found.add(name); pending.extend(row['callee'] for row in nodes[name]['calls'])
    return found

def assert_dag(nodes):
    done = set(); active = set()
    def visit(name):
        assert name in nodes, ('missing source edge', name)
        assert name not in active, ('reentrant source cycle', name)
        if name in done: return
        active.add(name)
        for edge in nodes[name]['calls']: visit(edge['callee'])
        active.remove(name); done.add(name)
    for name in nodes: visit(name)
    return len(done)

def inventory_audit():
    inv = js(CANDIDATE / 'inline-inventory.json')
    old = js(V / 'swift-guarded-snapshot-host-account-entry/caller-inventory.json')
    assert len(inv['caller_slots']) == 396
    cursor = 0; caller = collections.Counter(); caller_roles = collections.Counter()
    for index, function in enumerate(old['functions']):
        for role in function['roles']:
            row = inv['caller_slots'][cursor]; cursor += 1
            assert (row['id'], row['function'], row['local'], row['bytes'], row['phase']) == (f'caller19::{index}::{role["local"]}', function['header'], role['local'], role['bytes'], function['phase'])
            phase = 'P0' if row['phase'].startswith('P0') else 'child'
            caller[phase] += row['bytes']; caller_roles[phase] += 1
    assert cursor == 396 and caller == {'P0':234375, 'child':76696} and caller_roles == {'P0':208, 'child':188}
    leaf_source = js(V / 'swift-guarded-snapshot-leaf-shell-cost/operation-ledger.json')
    leaf_sizes = js(V / 'swift-guarded-snapshot-source146-leaf-payload-layouts/results.json')
    compact = lambda t: re.sub(r'(?:[A-Za-z_]\w*::)+', '', t).replace("'static", "'_")
    actual_sizes = collections.defaultdict(set)
    fresh = js(V / 'swift-guarded-snapshot-host-composition-independent/fresh-layout-results.json')
    for name, size in fresh['actual_type_sizes'].items(): actual_sizes[compact(name)].add(size)
    for row in leaf_sizes['queries']:
        for name in ['key', 'concrete']: actual_sizes[compact(row[name])].add(row['size'])
    def leaf_extent(t):
        if t in actual_sizes and len(actual_sizes[t]) == 1: return next(iter(actual_sizes[t]))
        if t.startswith(('&', '*const ', '*mut ')):
            inner = t[1:].removeprefix('mut ').strip() if t.startswith('&') else t.split(' ',1)[1]
            return 16 if inner == 'str' or inner.startswith('dyn ') or inner.startswith('[') and ';' not in inner else 8
        match = re.fullmatch(r'\[(.+); (\d+)\]', t)
        if match: return leaf_extent(match[1]) * int(match[2])
        raise AssertionError(('unclosed leaf type', t))
    cursor = 0; leaf = collections.Counter()
    for function in leaf_source['functions']:
        for local, role in function['roles'].items():
            row = inv['leaf_slots'][cursor]; cursor += 1
            assert row['id'] == f'leaf8::{function["function"]}::{local}'
            assert row['type'] == compact(role['compiler_type']) and row['bytes'] == leaf_extent(row['type'])
            leaf[function['function']] += row['bytes']
    assert cursor == 205 and sum(leaf.values()) == 320766 and leaf['leaf'] == 95850
    extracted = js(V / 'swift-guarded-snapshot-loader-work-source146/mir-extraction146.json')
    ledger = js(V / 'swift-guarded-snapshot-loader-work-source146/mir-ledger.json')
    assert set(extracted['functions']) == set(ledger['nodes']) and assert_dag(ledger['nodes']) == 219
    assert graph_closure(ledger['nodes'], ledger['roots']['loader']) == set(ledger['nodes'])
    validators = graph_closure(ledger['nodes'], ledger['roots']['validator'])
    assert len(validators) == 152
    table = layout_catalog(); roster = generic_roster(extracted)
    cursor = 0; total = 0; validator_bytes = 0; validator_roles = 0; generics = []
    for index, (name, function) in enumerate(sorted(extracted['functions'].items())):
        assert function['sha256'] == ledger['nodes'][name]['mir_sha256']
        for local, original in function['locals'].items():
            row = inv['loader_slots'][cursor]; cursor += 1
            assert (row['id'], row['function'], row['function_sha256'], row['local'], row['type'], row['validator']) == (f'loader219::{index}::{local}', name, function['sha256'], local, compact(original), name in validators)
            size = concrete_extent(original, table)
            if size is None:
                size, candidates = generic_extent(original, table, roster)
                assert size is not None, ('unclosed original type', name, local, original)
                assert sorted(row['layout_proof']['candidates']) == candidates
                generics.append({'function': name, 'local': local, 'original_type': original,
                                 'actual_candidates': candidates, 'maximum_bytes': size})
            proof = row['layout_proof']; key = proof['compiler_key']
            if key is not None: assert key in table
            assert row['known_bytes'] == size and row['required_layout'] is None, (name, local, original, size, row['known_bytes'])
            total += size
            if name in validators: validator_bytes += size; validator_roles += 1
    assert (cursor, total, validator_roles, validator_bytes, len(generics)) == (9403, 644008, 6458, 171197, 28)
    assert inv['required_layouts'] == [] and inv['leaf_work_native_occurrence_bytes_used'] == 0
    return {'caller_roles':dict(caller_roles), 'caller_bytes':dict(caller),
            'leaf_bodies':8, 'leaf_roles':205, 'leaf_bytes':dict(leaf),
            'loader_functions':219, 'loader_roles':cursor, 'loader_inline_bytes':total,
            'validator_functions':152, 'validator_roles':validator_roles, 'validator_inline_bytes':validator_bytes,
            'authored_call_edges':sum(len(x['calls']) for x in ledger['nodes'].values()),
            'all_authored_callback_edges_acyclic':True, 'generic_roster':roster,
            'generic_roles':generics, 'logical_declared_slots_not_operation_or_native_WORK_bytes':True}

def ordered(text, fragments):
    cursor = 0
    for fragment in fragments:
        where = text.find(fragment, cursor)
        assert where >= 0, ('missing or reordered source edge', fragment)
        cursor = where + len(fragment)

def source_edges(overrides=None):
    overrides = overrides or {}
    def src(name): return overrides.get(name, read(source_path(name)).decode())
    initial_name = 'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
    loader_name = 'src/experimental_swift_reactor/retained_profile_loader_v1.rs'
    account_name = 'src/experimental_swift_reactor/cache/initial_profile_v1/host_account_v1.rs'
    control_name = 'src/experimental_swift_reactor/control.rs'
    cache_name = 'src/experimental_swift_reactor/cache.rs'
    initial = src(initial_name); loader = src(loader_name); account = src(account_name)
    control = src(control_name); cache = src(cache_name)
    ordered(initial, ['let quote = host_account_v1::selected_whole_quote_v1()?;',
                      'let reservation = account.reserve_whole_v1(quote)?;',
                      'reservation.dispatch_v1(|| run_prepaid_fixture_v1(fixture))',
                      'fn setup_files_once_v1(', 'File::open(binding.paths[stage])'])
    ordered(initial, ['fn run_prepaid_fixture_v1(', 'setup_files_once_v1(binding)',
                      'let cancellation = Cancellation::default();', 'load_selected_retained_profile_v1(',
                      'let claims = copy_claims_v1(', 'cancellation.clone()', 'OwnedFixtureOutcomeV1::Loaded {'])
    ordered(loader, ['let executable = retained(', 'drop(executable);', 'let input = retained(',
                     'validate_swift_reactor(&input, budget, cancellation)',
                     'if !source_bytes_equal(&proof, &input)', 'final_metadata_recheck_v1(files, &identities)?;',
                     'Ok(SelectedValidatedProfileV1 {', 'proof,'])
    ordered(account, ['pub(super) fn destroy_owned_v1(mut self)', 'self.owned.take() { drop(owned); }',
                      'let reservation = self.reservation.take();', 'drop(self);',
                      'Some(DestroyedStorageV1 { reservation })'])
    ordered(account, ['impl<T> Drop for PrepaidOwnedV1', 'self.owned.take() { drop(owned); }',
                      'pub(super) struct DestroyedStorageV1', 'pub(super) fn release_destroyed_v1(self)',
                      'before.storage.checked_sub(self.reservation.storage)'])
    assert 'Err(RefusalV1::WholeQuotePending)' in account and 'Err(RefusalV1::RootPolicyPending)' in account
    assert 'part.work == 0 || part.storage == 0' in account and 'const COMPONENT_COUNT_V1: usize = 6;' in account
    ordered(control, ['if let Err(mut failure) = result {', 'drop(body);',
                      'let retirement = P::retire_tickets', 'failure.after_cleanup = Some(control.finish_owned_cleanup(None));'])
    ordered(control, ['pub(crate) fn drop_proof_with_wasi(', 'drop(body);',
                      'let source_result = self.refund_with_wasi', 'let metadata_result = self.refund_with_wasi'])
    ordered(control, ['pub(super) fn finish_v1(self)', 'outer.retire_v1(',
                      'scope_adopted_retirement=match adopted', 'SwiftFunctionCache::cleanup(',
                      'Err(failure)=>{cache_retirement=Some(failure);drop(cache);}',
                      'control.finish_owned_cleanup(observation)', 'SnapshotScopeFinishV1 {'])
    ordered(cache, ['impl Partial {', 'fn cleanup(mut self,', 'take(&mut self.slots)',
                    'take(&mut self.pins)', 'take(&mut self.patches)', 'drop(take(&mut self.index));',
                    'drop(take(&mut self.plans));', 'self.adopted.take()', 'drop_proof_with_wasi(adopted, observation)'])
    ordered(cache, ['drop(take(&mut cache.index));', 'drop(take(&mut cache.plans));',
                    'let SwiftFunctionCache {', 'control.drop_proof_with_wasi(adopted,'])
    # Fully typed returned structs have files/errors/usage and no proof/cache owner.
    start = initial.index('enum OwnedFixtureOutcomeV1 {'); end = initial.index('\n    fn run_one_fixture_v1', start)
    outcome = initial[start:end]
    assert all(x in outcome for x in ['ReturnedLoaderFilesV1', 'LoaderUsageV1', 'rows: File', 'snapshot: File', 'cancellation_owner: Cancellation', 'claims_owner: UnverifiedProfileDigestBytesV1', 'PrimaryOutcomeV1'])
    assert not any(x in outcome for x in ['ValidatedSwiftReactor', 'SwiftFunctionCache', 'AdoptedProof'])
    proof_source = src('src/experimental/swift.rs')
    ordered(proof_source, ['meter.reserve(Resource::Source, input.len(), cursor)?;',
                           '.try_reserve_exact(input.len())', 'source.capacity() != input.len()',
                           'let source = source.into_boxed_slice();', 'metadata::read(&source,'])
    buffer_source = src('src/experimental/account.rs')
    ordered(buffer_source, ['let bytes = capacity', 'meter.reserve(self.category, bytes, cursor)?;',
                            'next.try_reserve_exact(capacity)', 'next.capacity() != capacity',
                            'let old = std::mem::replace(&mut self.values, next);', 'drop(old);',
                            'meter.release(self.category, self.charged);'])
    paths = [initial_name, loader_name, account_name, control_name, cache_name,
             'src/experimental/swift.rs', 'src/experimental/account.rs',
             'src/experimental/metadata.rs', 'src/experimental/validate.rs']
    return {'source_files': [{'path':name, 'sha256':digest(read(source_path(name)))} for name in paths],
            'manual_source_semantics_reviewed':True,
            'checked_source_edges':['prepayment before first open', 'executable lifetime disjoint from input/proof',
              'input/proof coexistence through equality', 'actual files/error/Arc retained in late outcome',
              'adoption refusal destroys proof before diagnostic-only return', 'Partial failure cleanup',
              'explicit cache cleanup and raw Drop fallback', 'destruction token returned after payload and carrier drop',
              'private P0 retirement only; implicit Drop/unwind retains'],
            'source_matching_alone_authorizes_release':False}

def oracle_parts(values):
    """Unbounded-integer independent arithmetic for admissible synthetic cuts."""
    paths = values.paths
    p0 = 234375 + values.outer_parent_inline.bytes + values.outer_parent_owned_backing.bytes + values.reviewed_binding_object.bytes + values.immutable_identity_and_diagnostic_backing.bytes + sum(p.p0_backing_bytes.bytes for p in paths)
    budget = values.original_validation
    retained = values.build_file_bytes.bytes + values.session_file_bytes.bytes + max(values.executable_file_bytes.bytes, values.source_file_bytes.bytes + budget.source_bytes.bytes + budget.metadata_bytes.bytes + budget.scratch_bytes.bytes)
    parts = {'P1_setup':60256 + 6 * values.file_resource_backing_each.bytes + sum(p.open_temporary_bytes.bytes for p in paths),
             'P1_loader':644008 + retained + values.loader_native_temporaries.bytes + values.executable_open_temporary.bytes,
             'P2_arguments':544, 'P3_shell':224916,
             'P4_leaf':111770 + 1899541 + 54976,
             'P5_returned':values.error_owner_count.count * values.error_backing_each.bytes + values.all_payload_destructor_temporaries.bytes}
    return p0, parts, retained

def run_audit():
    return {'schema':1, 'custody':custody(), 'inventory':inventory_audit(),
            'source_lifetime_review':source_edges(), 'resource_source_supplement':resource_supplement(),
            'acceptance_scope':'conditional logical storage interface only',
            'actual_parent_or_fixture_values_qualified':False, 'root_policy_selected':False,
            'resource_candidate_acceptance_in_target':False, 'compiled_std_correspondence_pending':True,
            'new_compiler_product_native_or_UI_execution':False, 'whole_quote_or_GA':False}

if __name__ == '__main__':
    print(json.dumps(run_audit(), sort_keys=True))
