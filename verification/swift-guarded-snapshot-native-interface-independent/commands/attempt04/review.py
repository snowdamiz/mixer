"""Independent offline review. Reads released frozen data; writes only own lane.

No compiler, product/fixture/native execution, installed toolchain, live source,
other active lane, process inventory, Git or network is used. Candidate model
calls below are pure Python arithmetic/classification controls, not runtime
qualification. Independent expected formulas do not call candidate derivation.
"""
import copy
import datetime
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
C = ROOT / 'verification/swift-guarded-snapshot-native-interface-bounds'
SOURCE = '690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'
HOST = '027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2'
RUST = 'b940084d7eb6a299eb4bfeb8e34901bc051e7ac4'
SEAL = 'd02b6602bc7c4419d908db90a8e67d24b1dd3a46f9c9d2c2bb9158c70229b60f'
RELEASE = 'bcb2ce93d57fc74b968e979fb81947fc0d24ce12f689ae17df1b41e32255e313'
LIBC = 'b5b646652bf6661599e1da8901b3b9522896f01e736bad5f723fe7a3a27f899d'
checks = 0
methods = []
bindings = {}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(j):
    return json.dumps(j, sort_keys=True, separators=(',', ':')).encode()


def check(ok, label):
    global checks
    checks += 1
    if not ok:
        raise AssertionError(label)


def read(p):
    p = p if p.is_absolute() else ROOT / p
    check(not p.is_symlink(), ('symlink', str(p)))
    data = p.read_bytes()
    bindings[str(p.relative_to(ROOT))] = {'bytes': len(data), 'sha256': sha(data)}
    return data


def load(p):
    return json.loads(read(p))


def save(name, j):
    (HERE / name).write_text(json.dumps(j, indent=2, sort_keys=True) + '\n')


def method(name):
    methods.append(name)


def verify_seal(folder, expected=None):
    raw = read(folder / 'seal.json')
    if expected:
        check(sha(raw) == expected, ('seal', str(folder)))
    j = json.loads(raw)
    paths = [r['path'] for r in j['members']]
    check(len(paths) == len(set(paths)), ('duplicate-members', str(folder)))
    for r in j['members']:
        check(not Path(r['path']).is_absolute() and '..' not in Path(r['path']).parts, 'unsafe-member')
        data = read(folder / r['path'])
        check(len(data) == r['bytes'] and sha(data) == r['sha256'], ('member', str(folder), r['path']))
    return j


def main():
    method('candidate_and_exact_frozen_dependency_custody')
    release = load(ROOT / 'verification/swift-semantic-adapter-root-review/guarded-snapshot-native-interface-frozen-release.json')
    check(bindings['verification/swift-semantic-adapter-root-review/guarded-snapshot-native-interface-frozen-release.json']['sha256'] == RELEASE, 'root-release')
    seal = verify_seal(C, SEAL)
    check((len(seal['members']), sum(r['bytes'] for r in seal['members'])) == (115, 1255928), 'candidate-geometry')
    check(sha(canonical(seal['members'])) == seal['tree_sha256'], 'candidate-tree')
    roster = sorted(str(p.relative_to(C)) for p in C.rglob('*') if p.is_file() and p.name != 'seal.json')
    check(roster == sorted(r['path'] for r in seal['members']), 'complete-candidate-roster')
    check(release['amendment_selected'] is False and release['acceptance'] is False, 'unselected-release')
    custody = load(C / 'input-custody.json')
    check(custody['source_tree_sha256'] == SOURCE and custody['host_tree_sha256'] == HOST, 'source-host-binding')
    for r in custody['files']:
        data = read(Path(r['path']))
        check(len(data) == r['bytes'] and sha(data) == r['sha256'], ('custody', r['path']))
    packet_counts = []
    for r in custody['frozen_packets']:
        p = ROOT / r['path']
        j = verify_seal(p, r['seal_sha256'])
        check(len(j['members']) == r['members_verified'], ('packet-count', r['path']))
        packet_counts.append({'path': r['path'], 'members': len(j['members']), 'seal_sha256': r['seal_sha256']})
    source_map = load(Path('verification/swift-guarded-snapshot-loader-work-source146/source-reference-map.json'))
    manifest = load(Path('verification/swift-guarded-snapshot-host-composition/source-manifest.json'))
    check(len(source_map['members']) == 146 and manifest['tree_sha256'] == SOURCE, '146-source')
    check([{k:r[k] for k in ['path', 'bytes', 'sha256']} for r in source_map['members']] == manifest['members'], 'source-map-manifest')
    host = load(Path('verification/swift-guarded-snapshot-host-composition/host-support-manifest.json'))
    check(len(host['members']) == 11 and host['tree_sha256'] == HOST, 'host11')

    method('official_platform_and_libc_archival_checksums')
    fetch_refs = [
        (ROOT/'verification/swift-guarded-snapshot-stdlib-resource-source/fetch-receipt.json', 'files'),
        (ROOT/'verification/swift-guarded-snapshot-stdlib-resource-source/followup-fetch-receipt.json', 'files'),
        (ROOT/'verification/swift-guarded-snapshot-resource-cost/fetch-receipt.json', 'files'),
        (C/'fetch-receipt.json', 'files'),
    ]
    fetch_counts = []
    for p, key in fetch_refs:
        j = load(p)
        for r in j[key]:
            check(r['status'] == 200 and f'/{RUST}/' in r['url'], 'immutable-official-rust-ref')
            q = ROOT/r['path'] if r['path'].startswith('verification/') else p.parent/'official-source'/r['path']
            data = read(q)
            check(sha(data) == r['sha256'] and len(data) == r['bytes'], ('official-file', r['path']))
        fetch_counts.append({'receipt': str(p.relative_to(ROOT)), 'files': len(j[key])})
    check(fetch_counts[0]['files'] + fetch_counts[1]['files'] == 19, 'all19-inherited-platform-references')
    libc = load(C/'libc-fetch-receipt.json')
    check(libc['archive_sha256'] == LIBC and libc['status'] == 200, 'libc-archive-receipt')
    check(libc['url'] == 'https://static.crates.io/crates/libc/libc-0.2.183.crate', 'libc-version')
    for r in libc['members']:
        data = read(Path(r['path']))
        check(sha(data) == r['sha256'] and len(data) == r['bytes'], 'libc-selected-member')
    lock = read(C/'official-source/Cargo.lock').decode()
    check('name = "libc"\nversion = "0.2.183"' in lock and LIBC in lock, 'exact-lock-checksum')
    # The full crate archive is not retained here. This review rechecks selected
    # member bytes and the historical archive receipt/lock binding, not a new
    # download or a nonexistent archive. Rust notices are sealed members.

    method('verbatim_source_anchors_path_route_and_platform_ABI')
    sources = load(C/'source-evidence.json')['entries']
    for e in sources:
        raw = read(Path(e['path']))
        check(sha(raw) == e['file_sha256'], 'source-file-sha')
        block = b''.join(raw.splitlines(keepends=True)[e['first_line']-1:e['last_line']])
        check(block.decode() == e['source'] and sha(block) == e['excerpt_sha256'], 'verbatim-source-window')
    check(len(sources) == 23, '23-source-windows')
    evidence = {e['claim']:e['source'] for e in sources}
    small = read(ROOT/'verification/swift-guarded-snapshot-resource-cost/official-source/library/std/src/sys/helpers/small_c_string.rs').decode()
    check('#[cfg(not(target_os = "espidf"))]\nconst MAX_STACK_ALLOCATION: usize = 384;' in small, 'Darwin384-not-espidf32')
    check(small.index('bytes.len() >= MAX_STACK_ALLOCATION') < small.index('run_with_cstr_allocating(bytes, f)'), 'threshold-inclusive')
    cs = read(C/'official-source/library/alloc/src/ffi/c_str.rs').decode()
    start = cs.index('fn spec_new_impl_bytes(')
    body = cs[start:cs.index('impl SpecNewImpl for', start)]
    check(body.index('Vec::with_capacity(capacity)') < body.index('memchr::memchr(0, bytes)'), 'long-NUL-allocation-before-validation')
    check('Some(i) => Err(NulError(i, buffer))' in body, 'NUL-error-original-Vec')
    check('let capacity = bytes.len().checked_add(1).unwrap();' in body, 'exact-request-n-plus1')
    check('impl SpecNewImpl for &\'_ [u8]' in cs, 'borrowed-byte-specialization')
    setup = evidence['actual three input and two create_new output opens, retained failures']
    check('for stage in 0..5' in setup and 'if stage < 3' in setup, '3-plus2')
    check('OpenOptions::new().write(true).create_new(true).open(binding.paths[stage])' in setup, 'fixed-create-new')
    check('Err(original) => return SetupOutcomeV1::Refused { stage, original, files }' in setup, 'retained-prefix-original-error')
    check('.truncate(' not in setup, 'no-truncate')
    observer = evidence['fixed caller byte buffers; executable path first NUL and nonempty absolute checks']
    check('.position(|x| *x == 0)' in observer and 'executable_path.len == 0' in observer and 'executable_path.data[0] != b\'/\'' in observer, 'executable-first-NUL-nonempty-absolute')
    errno = read(C/'official-source/library/std/src/sys/io/error/unix.rs').decode()
    check('target_vendor = "apple"), link_name = "__error"' in errno, 'Apple-error-link')
    apple = read(C/'official-libc/src/unix/bsd/apple/mod.rs').decode()
    for s in ['pub type dev_t = i32;', 'pub type ino_t = u64;', 'pub type mode_t = u16;', 'pub type nlink_t = u16;', 'pub type blksize_t = i32;', 'pub type time_t = c_long;']:
        check(s in apple, ('Darwin-alias', s))
    bsd = read(C/'official-libc/src/unix/bsd/mod.rs').decode()
    check('pub type off_t = i64;' in bsd and 'pub type blkcnt_t = i64;' in bsd, 'Darwin-off-block')
    # Independent repr(C) layout in declaration order, including its padding.
    fields = [('dev',4,4),('mode',2,2),('nlink',2,2),('ino',8,8),('uid',4,4),('gid',4,4),('rdev',4,4)]
    fields += [(n,8,8) for n in ['atime','atime_nsec','mtime','mtime_nsec','ctime','ctime_nsec','birthtime','birthtime_nsec','size','blocks']]
    fields += [(n,4,4) for n in ['blksize','flags','gen','lspare']] + [('qspare',16,8)]
    at = 0
    stat = []
    for n, size, align in fields:
        at += (-at) % align
        stat.append({'field':n, 'bytes':size, 'alignment':align, 'offset':at})
        at += size
    stat_size = at + (-at) % 8
    details = load(C/'interface-derivation.json')
    check(stat_size == 144 and details['stat_repr_C_fields'] == stat, 'Darwin-stat144')
    layout = gzip.decompress(read(Path('verification/swift-guarded-snapshot-host-composition-independent/commands/exact146-metadata-mir/stdout.gz')))
    check(sha(layout) == '6c924c8088173db78afb1f648b284df7d8d139b3389bd090a9552df4130cfe7a', 'archived-source146-layout-sha')
    for l in ['print-type-size type: `std::io::Error`: 8 bytes, alignment: 8 bytes', 'print-type-size type: `std::fs::File`: 4 bytes, alignment: 4 bytes']:
        check(layout.splitlines().count(l.encode()) == 1, 'exact-qualified-archived-layout')

    method('independent_open_error_entry_and_executable_arithmetic')
    contract = load(C/'contract.json')
    fixed = [36,16,17,384,0,1,17,25,40,16,24,21,20,57,57,4,16]
    multiplicities = [0,0,0,0,2,0,1,1,0,0,0,1,0,1,1,0,0]
    check([r['fixed_bytes'] for r in contract['open_records']] == fixed, 'independent-fixed-record-roster')
    check([r['path_byte_multiplicity'] for r in contract['open_records']] == multiplicities, 'independent-path-byte-roster')
    check(sum(fixed) == 751 and sum(multiplicities) == 7 and len(fixed) == 17, 'open751-plus17-plus7n')
    check(sum(r['fixed_bytes'] for r in contract['error_records']) == 20 and len(contract['error_records']) == 3, 'error23')
    entry_constant = 119922 + 24 + 5*(751+17) + (20+3) + 53*1210256815
    check(entry_constant == 64143735004, 'entry-fold')
    check(details['entry_work_folded_constant'] == entry_constant, 'candidate-entry-fold')
    check(details['executable_open_interface']['source_max_public_interface_price'] == 768+7*4095 == 29433, 'separate-executable-work')
    check(details['executable_open_interface']['max_extra_CString_requested_heap_bytes'] == 4096, 'executable-request4096')
    check(4097 >= 4096 and contract['executable_open_separate'], 'conservative-executable-envelope')
    cvtr = evidence['private EINTR loop has no finite syscall attempt bound']
    check('loop {' in cvtr and 'Err(ref e) if e.is_interrupted() => {}' in cvtr, 'unbounded-private-EINTR')
    check(contract['private_std_syscall_retry_CPU_kernel_stack_RSS_bounded'] is False, 'no-private-retry-CPU-claim')

    method('complete_closed_resource_graph_and_uniform_operand_union')
    resource = load(Path('verification/swift-guarded-snapshot-resource-cost/contract.json'))
    row_data = load(Path('verification/swift-guarded-snapshot-resource-cost/rows.json'))
    rows = row_data['rows'] if isinstance(row_data, dict) else row_data
    internal = load(Path('verification/swift-guarded-snapshot-resource-cost/internal-rows.json'))
    check(len(rows) == 20 and len(internal['rows']) == 13, '20-plus13-complete-rows')
    inventory = load(Path('verification/swift-guarded-snapshot-payload-destruction-cost/inventory.json'))
    declared = {d['name']:d for d in inventory['declarations']}
    src_by_path = {r['path'].removeprefix('vm/'):ROOT/r['source'] for r in source_map['members']}
    # Authenticate archived declaration fragments against the frozen source, then
    # trace dynamic element type fields, rather than infer one resource per enum.
    decl_bindings = []
    for d in inventory['declarations']:
        p = src_by_path.get(d['path'])
        if p is None:
            p = src_by_path.get('vm/'+d['path'])
        check(p is not None, ('declaration-source-path', d['path']))
        text = read(p).decode()
        # Inventory hashes the comment-elided declaration, rather than a raw
        # contiguous file window. The entire raw file is separately SHA bound.
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
        text = '\n'.join(line.split('//',1)[0] for line in text.splitlines())
        # The accepted graph gives unrelated Span/Resource declarations
        # explicit names while retaining their original declaration hashes.
        source_name = {'MetaSpan':'Span','WasiSpan':'Span','ValidatorResource':'Resource'}.get(d['name'],d['name'])
        needle = d['kind']+' '+source_name
        starts = [m.start() for m in re.finditer(re.escape(needle)+r'\b', text)]
        matched = [text[i:i+d['source_bytes']] for i in starts if sha(text[i:i+d['source_bytes']].encode()) == d['declaration_sha256']]
        check(len(matched) == 1, ('declaration-source-hash', d['name']))
        decl_bindings.append({'name':d['name'], 'source_path':str(p.relative_to(ROOT)), 'declaration_sha256':d['declaration_sha256']})
    primitives = {'u8','u16','u32','u64','u128','usize','i8','i16','i32','i64','i128','isize','bool','f32','f64','str','AtomicBool'}
    wrappers = {'Option','Result','Vec','Box','Arc'}
    def plain_trace(t, seen=None):
        seen = set() if seen is None else set(seen)
        names = re.findall(r'[A-Za-z_][A-Za-z_0-9]*(?=\s*(?:<|>|,|\]|;|$))', t)
        for name in names:
            check(name != 'Error', ('dynamic-element-Error', t))
            if name in primitives or name in wrappers or name in seen:
                continue
            check(name in declared, ('unclosed-dynamic-element', name, t))
            d = declared[name]
            seen.add(name)
            fields = d.get('fields', []) + [f for v in d.get('variants', []) for f in v['fields']]
            for field in fields:
                plain_trace(field, seen)
    vector_types = sorted(resource['vectors'])
    for vector in vector_types:
        plain_trace(vector[4:-1])
    check(len(vector_types) == 14, 'all14-vector-frontiers')
    rf = {name:sum(sum(r['native_fields'].values()) for r in v['records']) for name,v in resource['interfaces'].items()}
    check(rf == {'File':73,'Error':32,'Arc<AtomicBool>':149}, 'native-resource-byte-unions')
    check(resource['Error_provenance'] == 'closed-file-os-or-static-message' and resource['arbitrary_custom_error_accepted'] is False, 'closed-Error-provenance')
    check(all(r['known_statically_reachable_product_authored_drop_callbacks'] == 0 for r in rows), 'closed-product-Drop')
    for h in inventory['observed_production_authored_drop_headers']:
        check(any(x in h for x in ['PrepaidOwnedV1', 'SessionLease', 'session::Reservation']), 'no-reachable-payload-custom-Drop')
    unions = []
    all_rows = rows + internal['rows']
    allowed = set(vector_types)|{'Box<[u8]>','File','Error','Arc<AtomicBool>'}
    def union(row):
        value = row['inline_bytes']
        for name,count in row['resource_frontiers'].items():
            check(name in allowed and type(count) is int and count > 0, 'known-positive-frontier')
            unit = rf[name] if name in rf else 24
            if name == 'Vec<SwiftSlot>':
                d = row['dynamic_resource_elements'][name]
                check(d['inline_bytes'] == 136 and d['resource_frontiers'] == {'Vec<DecodedInstruction>':1,'Vec<Type>':1,'Vec<u32>':1}, 'complete-nested-three-vectors')
                unit += resource['vectors'][name]['max_live_elements']*union(d)
            value += count*unit
        return value
    for r in all_rows:
        unions.append({'type':r['type'], 'native_interface_operand_union_bytes':union(r)})
    expected_rows = [{'type':r['type'],'native_interface_operand_union_bytes':r['native_interface_operand_union_bytes']} for r in details['payload_drop_rows']]
    check(unions == expected_rows, 'all33-unions-independent-recomputed')
    maximum = max(r['native_interface_operand_union_bytes'] for r in unions)
    check(maximum == 29394 and [r['type'] for r in unions if r['native_interface_operand_union_bytes'] == maximum] == ['SnapshotRunV1'], 'uniform29394')
    loader_operands = [28,4+8+4+144,24,60,12,8,8,4120,4120,32]
    check(sum(loader_operands) == 8572 and [r['fixed_bytes'] for r in details['loader_native_records']] == loader_operands, 'loader8572')
    amendment = load(C/'storage-interface-amendment.json')
    check(amendment['file_resource_backing_each'] == 73 and amendment['error_backing_each'] == 32 and amendment['loader_native_temporaries'] == 8572 and amendment['all_payload_destructor_temporaries'] == 29394, 'amendment-operands')
    for key in ['closed_error_owned_backing_bytes','file_owned_extra_backing_bytes','all_transitive_payload_drop_extra_requested_heap_bytes','loader_native_helpers_extra_requested_heap_bytes']:
        check(contract[key] == 0, ('exact-extra-requested-heap-zero', key))
    check(amendment['exact_extra_requested_heap_bytes_for_each_of_those_four_interfaces'] == 0 and amendment['selection_and_compiled_correspondence_pending'] is True, 'amendment-not-invented-heap-or-selected')

    method('simultaneous_Error_owner_envelope_without_work_multiplier')
    storage = load(Path('verification/swift-guarded-snapshot-host-storage-composition/results.json'))
    subtotal = storage['caller_inline_bytes'] + storage['leaf_inline_bytes'] + storage['loader_inline_bytes'] + storage['full_product_retention']
    check(subtotal == 311071+320766+644008+1899541 == 3175386, 'complete-frame-and-retention-sum')
    check(storage['loader_functions'] == 219 and storage['original_validator_functions'] == 152, 'validator-within-complete-loader-closure')
    nerrors = subtotal//8+1
    check(nerrors == 396924 and amendment['error_owner_count'] == nerrors, '396924-disjoint8-plus-transfer')
    check(nerrors*8 > subtotal and (nerrors-1)*8 <= subtotal, 'floor-plus1')
    check(amendment['error_count_derivation']['future_outer_parent_foreign_Error_not_included'], 'outer-parent-separate')
    check(amendment['error_count_derivation']['native_helper_originals_additional'] == 1, 'one-private-helper-original-transfer')
    check(storage['native_work_bytes_used_for_storage'] == 0, 'no-work-to-storage')

    method('adverse_pure_model_cases_and_non_authorizing_custody')
    spec = importlib.util.spec_from_file_location('native_interface_candidate_model', C/'model.py')
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    def refused(fn, *args):
        try:
            fn(*args)
        except (m.Refused, TypeError, ValueError):
            check(True, 'expected-refusal')
        else:
            check(False, ('missing-refusal', fn.__name__, args))
    def path(n, b=None):
        return m.PathExtent(n, n if b is None else b, 'synthetic-only-not-actual-custody')
    cases = []
    for n in list(range(0,512))+[1023,4095,4096,4097,8192,65535,100000,2**31]:
        b = m.path_bounds(path(n), contract)
        check(b['price'] == 768+7*n, 'oracle-open-formula')
        check(b['extra_requested_heap_bytes_max'] == (n+1 if n >=384 else 0), 'oracle-heap-path')
        check(b['positive_conversion_interface_envelope'] == max(384,n+1), 'oracle-path-operand-envelope')
        check(b['finite_private_open_syscall_attempt_bound'] is False, 'private-retries-flag')
        if n <= 100000:
            for raw in [b'x'*n, b'\xff'*n] + ([b'x'*(n//2)+b'\0'+b'x'*(n-n//2-1)] if n else []):
                result = m.path_case(raw)
                check(result['semantic_open_requests'] == int(b'\0' not in raw), 'NUL-stops-open')
                check(result['heap_request_bytes'] == (n+1 if n>=384 else 0), 'long-NUL-request-still-present')
                check(result['utf8_required'] is False and result['retained_error_heap_bytes'] == 0, 'raw-bytes-static-error')
        if n in [0,1,383,384,385,4095,4096,4097]:
            cases.append({'n':n,'price':b['price'],'extra_heap':b['extra_requested_heap_bytes_max'],'positive_operand_envelope':b['positive_conversion_interface_envelope']})
    for fail in range(5):
        options = ['read-only' if k<3 else 'write-create_new' for k in range(fail+1)]
        retained = tuple(range(fail))
        check(len(options) == fail+1 and len(retained) == fail and fail not in retained, 'setup-prefix-failure-no-new-owner')
    paths = tuple(path(n) for n in [0,383,384,4097,100000])
    entry = m.child_entry(paths,contract,1210256815)
    check(entry['entry_price'] == entry_constant+7*sum(p.encoded_bytes for p in paths), 'entry-oracle')
    for i in range(5):
        more = list(paths)
        more[i] = path(paths[i].encoded_bytes+1)
        check(m.child_entry(tuple(more),contract,1210256815)['entry_price'] == entry['entry_price']+7, 'entry-monotonic')
    for bad in [True,False,-1,2**64,None,1.0,'1']:
        refused(m.path_bounds,path(bad),contract)
    for n in [(1<<63)-1,(1<<63)-2,((1<<64)-1-768)//7+1]:
        refused(m.path_bounds,path(n),contract)
    nmax = ((1<<64)-1-768)//7
    check(m.path_bounds(path(nmax),contract)['price'] <= (1<<64)-1, 'max-fitting-path-price')
    for bad in [0,-1,True,None,'1',2**64-1]:
        refused(m.child_entry,paths,contract,bad)
    refused(m.path_bounds,path(4,3),contract)
    refused(m.path_bounds,m.PathExtent(1,1,''),contract)
    refused(m.child_entry,paths[:4],contract,1210256815)
    for field, value in [('setup_truncate',True),('path_branch_threshold',4096),('closed_error_owned_backing_bytes',32),('private_std_syscall_retry_CPU_kernel_stack_RSS_bounded',True)]:
        mutated = copy.deepcopy(contract)
        mutated[field] = value
        refused(m.path_bounds,path(3),mutated)
    refused(m.closed_extra_requests,'foreign',{'Error':1})
    for foreign in ['Vec<CustomDrop>','Box<Callback>','Arc<Foreign>','Error<callback>']:
        refused(m.closed_extra_requests,'source146-owned-file-route',{foreign:1})
    for row in all_rows:
        check(m.closed_extra_requests('source146-owned-file-route',row['resource_frontiers'])['extra_requested_heap_bytes'] == 0, 'closed-row-zero-extra-request')
    ps = (m.Pointee('synthetic-string',0,0,'synthetic-only'),)
    check(m.p0_bounds(paths,512,ps)['reviewed_binding_object_bytes'] == 512, 'source-minimum-binding')
    refused(m.p0_bounds,paths,511,ps)
    refused(m.p0_bounds,paths,512,())
    refused(m.p0_bounds,paths,512,(ps[0],ps[0]))
    # Nonempty labels are proof obligations only. This evaluator cannot prove
    # roster completeness, authentic identities, actual bytes, or P0 funding.
    check(m.path_bounds(path(0,0),contract)['p0_backing_bytes'] == 0, 'empty-source-path-permits-zero-backing')

    method('preserved_failures_and_limits')
    attempts = load(C/'attempt-history.json')
    check(attempts['failures_preserved'] == 4, 'four-producer-checker-failures')
    for r in attempts['attempts']:
        receipt = load(C/r['path']/'receipt.json')
        check(receipt['exit_code'] == r['exit_code'] and receipt['waited'] and receipt['owned_process_group_absent'], 'producer-attempt-preserved')
        read(C/r['path']/'stdout')
        read(C/r['path']/'stderr')
    limits = [
        'Root must explicitly select the positive native operand allowance amendment; this review proposes it and does not select it.',
        'File73/Error32/loader8572/teardown29394 are conservative source operand unions. Additional explicit requested heap for each is exactly zero. They are not heap measurements, physical stack, arbitrary positive prices, or work multipliers.',
        'The396924 Error count is a conservative disjoint8-byte owner envelope for complete closed authored frames/retention plus one helper original. Foreign callbacks/Errors and future outer-parent owners remain excluded and require separate P0 bounds.',
        'The uniform29394 operand envelope covers all33 complete typed rows and all64 SwiftSlot nested elements, with existing backing deallocated rather than newly allocated.',
        'Actual P0 parent, paths, complete immutable binding/identity/diagnostic pointees, file/build/session/executable extents and identities are independently pending. Nonempty custody strings cannot authenticate them.',
        'Private EINTR retries have no finite attempt bound. Public semantic-open logical pricing is not syscall-count, CPU, time, RSS, physical-stack, allocator/kernel/private-runtime, or panic/OOM-hook pricing.',
        'OOM/infallible CString allocation failure is not returned io::Error or healthy refusal. Panic, allocator failure hooks and unwinding machinery remain outside the logical unit.',
        'Source authority does not establish installed binary or actual caller correspondence. Binary-correspondence active lane was not read.',
        'No source/product runtime, native simulator/emulator, UI/capture, real fixture execution/healthy cleanup, refunds, FieldLog, OTA, operational or GA acceptance.'
    ]
    review = {
        'schema':1,
        'status':'independent-source-interface-review-passed-conditional-amendment-recommended-not-selected',
        'candidate':{'path':str(C.relative_to(ROOT)), 'seal_sha256':SEAL, 'members':115, 'bytes':1255928, 'root_release_sha256':RELEASE},
        'source_tree_sha256':SOURCE, 'host_tree_sha256':HOST, 'rust_revision':RUST,
        'methods':len(methods), 'method_names':methods, 'assertions':checks, 'all_passed':True,
        'blocking_findings':[],
        'observations':[
            {'id':'amendment-required','severity':'condition','detail':limits[0]+' '+limits[1]},
            {'id':'actual-data-custody-pending','severity':'scope','detail':limits[4]},
            {'id':'archive-limits','severity':'scope','detail':'All19 inherited platform references,4 resource follow-up Rust files,9 added Rust files and9 selected libc members were rehashed. The full libc archive is not retained in the candidate; its checksum binding is the frozen fetch receipt and exact Cargo.lock, not a new network verification.'},
        ],
        'native_open_expression':'768+7*n', 'error_native':23, 'entry_expression':'64143735004+7*sum(five_actual_encoded_lengths)',
        'proposed_amendment':{'File_operand_allowance':73,'Error_operand_allowance':32,'loader_operand_allowance':8572,'uniform_teardown_operand_allowance':29394,'extra_requested_heap_each':0,'error_owner_count':396924},
        'complete_typed_rows':33, 'amendment_selected':False, 'whole_root_policy_quote_or_grant':False,
        'actual_paths_P0_identity_selected':False, 'compiled_binary_correspondence_verified_here':False,
        'private_syscall_retry_or_CPU_bound':False, 'native_runtime':'paused', 'GA_verified':False,
        'limitations':limits,
    }
    save('review.json',review)
    save('independent-derivation.json',{'schema':1,'entry_constant':entry_constant,'open_events':17,'open_fixed_operand_bytes':751,'path_multiplicity':7,'error_events':3,'error_operand_bytes':20,'stat_layout':stat,'stat_size':144,'source_windows':23,'source_window_unique_files':len({e['path'] for e in sources}),'official_fetch_receipts':fetch_counts,'libc_members':len(libc['members']),'closed_vector_types':vector_types,'declarations_bound':len(decl_bindings),'declarations':decl_bindings,'all_typed_unions':unions,'uniform_max':maximum,'owner_envelope_terms':{'caller':311071,'leaf':320766,'complete_loader_including_validator':644008,'product_retention':1899541},'owner_envelope_sum':subtotal,'owner_count':nerrors,'path_boundary_cases':cases,'frozen_dependency_packets':packet_counts})
    save('input-bindings.json',{'schema':1,'source_tree_sha256':SOURCE,'files':[dict(path=p,**v) for p,v in sorted(bindings.items())]})
    print(json.dumps({'all_passed':True,'methods':len(methods),'assertions':checks,'candidate_seal':SEAL,'source_tree_sha256':SOURCE,'root_amendment_selected':False,'native_product_execution':False},sort_keys=True))


if __name__ == '__main__':
    main()
