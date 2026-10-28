"""Offline integrity audit accompanying a manual, four-function local-facts review.

Only Python stdlib file/text/hash work. This does not import analyzed code, run
the region verifier, authorize an OTA, or compute a numeric region union.
"""
from pathlib import Path
import hashlib
import json
import signal
import sys
import time

signal.alarm(50)
START = time.monotonic()
ROOT = Path('/Users/andreyyurlov/Documents/dev/mixer')
OUT = ROOT / 'verification/swift-retained-geometry-independent'
MAX_RAW = 128 * 1024 * 1024
MAX_DERIVED = 8 * 1024 * 1024
SOURCE_TREE = '91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f'
PACKETS = {
    'swift-retained-geometry-caller-closure': '31c93475b603342a50d943d8050ff43cdcfe932703bd56fb10f8785b7c09f964',
    'swift-retained-geometry-dispatch-body': '0824b778f47268ddf3f94d6a51ee5f6d64553efb0440d89179012c0824ec3517',
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def load(name):
    return json.loads((ROOT / name).read_bytes())


def pin(name):
    path = ROOT / name
    assert path.is_file() and not path.is_symlink(), name
    h = hashlib.sha256()
    size = 0
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            size += len(chunk)
            h.update(chunk)
    assert size == path.stat().st_size, name
    return {'path': name, 'bytes': size, 'sha256': h.hexdigest()}


def check_pin(row, prefix=''):
    actual = pin(prefix + row['path'])
    assert (actual['bytes'], actual['sha256']) == (row['bytes'], row['sha256']), actual['path']
    return actual


def write(name, value):
    data = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    assert len(data) <= MAX_DERIVED
    (OUT / name).write_bytes(data)


sealed = []
json_members = []
for packet, expected in PACKETS.items():
    prefix = 'verification/' + packet + '/'
    seal_pin = pin(prefix + 'seal.json')
    assert seal_pin['sha256'] == expected
    seal = load(prefix + 'seal.json')
    assert seal['source146_tree_sha256'] == SOURCE_TREE
    rows = seal['members']
    assert len({r['path'] for r in rows}) == len(rows)
    assert sum(r['bytes'] for r in rows) == seal['member_bytes']
    tree_key = 'tree_sha256' if 'tree_sha256' in seal else 'tree_sha256_canonical_compact_JSON'
    assert digest(canonical(rows)) == seal[tree_key]
    actual_names = {str(p.relative_to(ROOT / prefix)) for p in (ROOT / prefix).rglob('*') if p.is_file()}
    assert actual_names == {r['path'] for r in rows} | {'seal.json'}
    sealed.append(seal_pin)
    for row in rows:
        sealed.append(check_pin(row, prefix))
        if row['path'].endswith('.json'):
            json_members.append(prefix + row['path'])

manifest_path = 'verification/swift-guarded-snapshot-root-result-lifetime-implementation/source-manifest.json'
manifest = load(manifest_path)
assert len(manifest['members']) == manifest['member_count'] == 146
assert digest(canonical(manifest['members'])) == manifest['tree_sha256'] == SOURCE_TREE
source_pins = [check_pin(row, 'verification/swift-guarded-snapshot-root-result-lifetime-implementation/source/vm/') for row in manifest['members']]

mapping_prefix = 'verification/swift-retained-capture-terminal-mapping/'
mapping_seal = pin(mapping_prefix + 'seal.json')
assert mapping_seal['sha256'] == '5ec27f9a01bc046341bd0833044d10c0803ce546f9607dc2595e423c0a5fe569'
mapping = load(mapping_prefix + 'target-map.json')
targets = {row['id']: row for row in mapping['targets']}
assert set(targets) == {'Caller', 'Closure', 'Dispatch', 'Body'}
raw_files = {}
for row in targets.values():
    for kind, field in [('ir', 'llvm_definition'), ('asm', 'assembly_function')]:
        raw_files[kind] = row[field]['file']
raw_pins = {kind: check_pin(row) for kind, row in raw_files.items()}
assert sum(row['bytes'] for row in raw_pins.values()) == 111430754 <= MAX_RAW


def span_bytes(kind, begin, end, expected):
    assert kind in raw_files and 0 <= begin < end <= raw_files[kind]['bytes']
    assert end - begin <= MAX_DERIVED
    with (ROOT / raw_files[kind]['path']).open('rb') as stream:
        stream.seek(begin)
        raw = stream.read(end - begin)
    assert len(raw) == end - begin and digest(raw) == expected, (kind, begin, end)
    return raw


whole_spans = []
texts = {}
for target, row in targets.items():
    for kind, field, suffix in [('ir', 'llvm_definition', 'll'), ('asm', 'assembly_function', 's')]:
        span = row[field]
        raw = span_bytes(kind, span['byte_begin'], span['byte_end'], span['span_sha256'])
        assert raw == (ROOT / mapping_prefix / 'excerpts' / (target + '.' + suffix)).read_bytes()
        assert len(raw.splitlines()) == span['line_end_inclusive'] - span['line_begin'] + 1
        assert raw.startswith(b'define ') and raw.endswith(b'}\n') if kind == 'ir' else raw.endswith(b'\t.cfi_endproc\n')
        assert row['symbol'].encode() in raw.splitlines()[0]
        if kind == 'asm':
            assert raw.splitlines()[0].decode() == row['assembly_symbol'] + ':'
        else:
            assert ('!dbg !' + str(row['definition_debug_id'])).encode() in raw.splitlines()[0]
        texts[target, kind] = raw.decode().splitlines()
        whole_spans.append({'target': target, 'artifact': kind, **span})
    source = row['source']
    check_pin(source['file'])
    with (ROOT / source['file']['path']).open('rb') as stream:
        stream.seek(source['byte_begin'])
        source_raw = stream.read(source['byte_end'] - source['byte_begin'])
    assert digest(source_raw) == source['span_sha256']
    assert source_raw == (ROOT / mapping_prefix / 'excerpts' / (target + '.rs')).read_bytes()

exception = load(mapping_prefix + 'body-exception-table.json')['span']
exception_raw = span_bytes('asm', exception['byte_begin'], exception['byte_end'], exception['span_sha256'])
assert exception_raw == (ROOT / mapping_prefix / 'excerpts/Body-exception-table.s').read_bytes()

# Stream lines without materializing the full IR or assembly as derived data.
# All saved debug records and whole-function global line coordinates are exact.
debug_records = load(mapping_prefix + 'debug-map.json')['records']
caller_debug = load('verification/swift-retained-geometry-caller-closure/debug-bindings.json')['records']
debug_by_line = {row['line']: row['text'] for row in debug_records + caller_debug}
line_boundaries = {'ir': {}, 'asm': {}}
for span in whole_spans:
    kind = span['artifact']
    line_boundaries[kind][span['byte_begin']] = span['line_begin']
    line_boundaries[kind][span['byte_end']] = span['line_end_inclusive'] + 1
debug_matches = 0
for kind in ['ir', 'asm']:
    seen_boundaries = set()
    offset = 0
    with (ROOT / raw_files[kind]['path']).open('rb') as stream:
        for number, line in enumerate(stream, 1):
            if offset in line_boundaries[kind]:
                assert number == line_boundaries[kind][offset]
                seen_boundaries.add(offset)
            if kind == 'ir' and number in debug_by_line:
                assert line.decode().rstrip('\n') == debug_by_line[number]
                debug_matches += 1
            offset += len(line)
    assert seen_boundaries == set(line_boundaries[kind])
assert debug_matches == len(debug_by_line)
debug_by_id = {row['id']: row['text'] for row in debug_records + caller_debug}
for target, row in targets.items():
    definition = debug_by_id[row['definition_debug_id']]
    assert row['symbol'] in definition
    assert ('file: !' + str(row['debug_source_file_id'])) in definition

# Recheck every supplied raw-range anchor, including instruction and call/exit
# anchors, rather than relying on a screen display or producer's assertion.
anchor_count = 0
anchor_distinct = set()


def walk(value):
    global anchor_count
    if isinstance(value, dict):
        if {'artifact', 'begin', 'end', 'sha256'} <= set(value):
            kind, begin, end, expected = (value[k] for k in ['artifact', 'begin', 'end', 'sha256'])
            raw = span_bytes(kind, begin, end, expected)
            anchor_count += 1
            anchor_distinct.add((kind, begin, end, expected))
            if 'text' in value:
                assert raw.decode().rstrip('\n') == value['text']
        for child in value.values():
            walk(child)
    elif isinstance(value, list):
        for child in value:
            walk(child)


for name in json_members:
    walk(load(name))

caller_dir = 'verification/swift-retained-geometry-caller-closure/'
db_dir = 'verification/swift-retained-geometry-dispatch-body/'
call_inventory = {}
for target in ['Caller', 'Closure']:
    inventory = load(caller_dir + target.lower() + '-call-sites.json')
    native = [line for line in texts[target, 'asm'] if line.strip().startswith('bl\t')]
    llvm = [line for line in texts[target, 'ir'] if line.strip().startswith('call ')]
    assert native == [row['text'] for row in inventory['native_call_sites']]
    assert llvm == [row['text'] for row in inventory['IR_call_sites']]
    call_inventory[target] = {'native': len(native), 'ir_including_intrinsics': len(llvm)}
edges = load(db_dir + 'edges-and-exits.json')
for target in ['Dispatch', 'Body']:
    native = [line.strip() for line in texts[target, 'asm'] if line.strip().startswith('bl\t')]
    llvm = [line.strip() for line in texts[target, 'ir'] if not line.lstrip().startswith(';') and (' call ' in line or line.strip().startswith('call ') or ' invoke ' in line or line.strip().startswith('invoke '))]
    assert native == [row['instruction'] for row in edges['native_and_IR_call_inventory'][target]['asm']]
    assert llvm == [row['instruction'] for row in edges['native_and_IR_call_inventory'][target]['ir']]
    call_inventory[target] = {'native': len(native), 'ir_including_intrinsics': len(llvm)}

facts = load(caller_dir + 'facts.json')
dispatch = load(db_dir + 'dispatch-facts.json')
body = load(db_dir + 'body-facts.json')
join = load(db_dir + 'cross-lane-candidate-join.json')
assert facts['Caller']['fixed_reservation_bytes'] == 32 + 3 * 4096 + 1680 == 14000
assert facts['Closure']['fixed_reservation_bytes'] == 48
assert dispatch['frame']['native_reserved_bytes_candidate'] == 32 + 10 * 4096 + 32 == 41024
assert body['frame']['native_reserved_bytes_candidate'] == 32 + 15 * 4096 + 2448 == 63920
assert not body['frame']['complete_native_all_exit_restoration_claimed']
assert body['frame']['normal_exit_restores_entry_sp'] is True
assert body['admitted_return']['local_alloca_13624_exists'] is False
assert facts['alignment']['known_physical_base_congruences'] == []
assert facts['alignment']['physical_alignment_for_candidate_native_arenas'] is None
assert facts['alignment']['numeric_local_union_allowed'] is False
assert join['numeric_union'] is None
assert join['composed_coordinates_candidates']['BodyEntrySP_minus_CallerEntrySP'] == -14000 - 41024 - 48
assert join['composed_coordinates_candidates']['R_minus_BodyEntrySP'] == 104
assert join['composed_coordinates_candidates']['C_minus_CallerEntrySP'] == -13840

# Expected slot offsets were independently traced from complete assembly/IR by
# the reviewer. These comparisons freeze the reviewed packet, not a new model.
expected_body_slots = [216,220,224,228,232,236,256,296,336,13952,13992,14000,15264,15304,16568,17832,19120,19152,20416,20840,20844,20848,20856,21112,21248,34864,36152,36576,50192,63809,63810,63811,63812,63813,63814,63815,63816,63824,63832,63840,63852,63856,63860,63864,63868,63872]
assert [row['final_sp_offset'] for row in body['frame']['native_slots']] == expected_body_slots
assert len(body['llvm_allocas']) == len(body['frame']['native_slots']) == 46
assert [row['final_sp_offset'] for row in dispatch['frame']['native_slots']] == [56,13680,13728,27352,40976]
assert len(dispatch['llvm_allocas']) == 5
for target, data in [('Dispatch', dispatch), ('Body', body)]:
    frame = data['frame']
    reservation = frame['native_reserved_bytes_candidate']
    for row in frame['native_slots'] + frame['native_spills']:
        assert row['entry_sp_offset'] == row['final_sp_offset'] - reservation
        assert 0 <= row['final_sp_offset'] < row['final_sp_offset'] + row['capacity_bytes'] <= reservation
for row in facts['Caller']['slots']:
    assert row['entry_sp_offset'] == row['sp_relative_offset'] - 14000

failure = load(db_dir + 'preparation-attempt-1.json')
assert failure['exit_code'] == 1 and failure['previous_attempt_posthash_or_seal_completed'] is False
assert failure['expected_preliminary_peer_seal_sha256'] == '6468bc27948ecc37db7a63982de6c48de2ed94934828f21590321da9cd7854c2'
assert failure['current_final_peer_seal_sha256'] == PACKETS['swift-retained-geometry-caller-closure']

readiness = load(db_dir + 'verifier-readiness.json')
capture_plan_path = 'verification/swift-root-bound-dispatch-retained-capture-v1/plan.json'
capture_plan = load(capture_plan_path)
original_plan = load(capture_plan['original_capture_plan']['path'])
check_pin(capture_plan['original_capture_plan'])
check_pin(capture_plan['base_capture_plan'])
assert digest(canonical(capture_plan['argv'])) == capture_plan['argv_sha256_canonical_JSON'] == readiness['actual_alternate_argv_sha256']
assert digest(canonical(original_plan['argv'])) == original_plan['argv_sha256_canonical_JSON'] == readiness['original_v2_argv_sha256']
assert capture_plan['argv'][:-3] == original_plan['argv'][:-1]
assert capture_plan['argv'][-3:-1] == ['-C', 'link-dead-code=yes']
assert capture_plan['argv'][-1].startswith('--emit=llvm-ir=')
assert original_plan['argv'][-1].startswith('--emit=llvm-ir=')
assert capture_plan['compiler'] == original_plan['compiler']
assert {k: v for k, v in capture_plan['environment'].items() if k != 'TMPDIR'} == {k: v for k, v in original_plan['environment'].items() if k != 'TMPDIR'}
assert capture_plan['environment']['TMPDIR'] == capture_plan['owned_output_directory'] + '/tmp'
assert original_plan['environment']['TMPDIR'] == original_plan['owned_output_directory'] + '/tmp'
assert capture_plan['source_tree_sha256'] == original_plan['source_tree_sha256'] == SOURCE_TREE
write('configuration-review.json', {
    'schema': 1,
    'alternate_plan': pin(capture_plan_path),
    'original_capture_plan': capture_plan['original_capture_plan'],
    'alternate_base_plan': capture_plan['base_capture_plan'],
    'original_argv': original_plan['argv'],
    'alternate_argv': capture_plan['argv'],
    'changed_compiler_option': ['-C', 'link-dead-code=yes'],
    'other_recorded_argv_difference': 'Exact llvm-ir/asm output paths move from original command directory to alternate-owned command directory; neither argv is relabeled.',
    'same_compiler_and_source_tree': True,
    'same_environment_except_owned_TMPDIR': True,
    'original_environment': original_plan['environment'],
    'alternate_environment': capture_plan['environment'],
    'compiler_version_from_saved_pinned_plan_only': capture_plan['version_from_prior_pinned_receipt'],
    'original_verifier_invoked': False,
})
verifier_path = 'verification/swift-root-bound-dispatch-physical-evidence-v2/source/region_certificate.py'
verifier_text = (ROOT / verifier_path).read_text()
assert readiness['original_v2_capture_plan_sha256'] in verifier_text
assert readiness['original_v2_argv_sha256'] in verifier_text
assert "need(same(binding,expected_binding),'source/compiler/cfg/inspection binding')" in verifier_text
assert "obj(binding,'source_tree compiler_commit target features fixture_cfg opt_level mir_opt_level overflow_checks panic codegen_units debuginfo capture_plan_sha256 argv_sha256')" in verifier_text
assert readiness['actual_alternate_capture_plan_sha256'] != readiness['original_v2_capture_plan_sha256']
assert readiness['actual_alternate_argv_sha256'] != readiness['original_v2_argv_sha256']
host_source = 'verification/swift-guarded-snapshot-root-result-lifetime-implementation/source/vm/src/experimental_swift_reactor/cache/initial_profile_v1/host_account_v1.rs'
assert 'Err(RefusalV1::WholeQuotePending)' in (ROOT / host_source).read_text().splitlines()[75]

tracked = {row['path']: row for row in sealed + source_pins + list(raw_pins.values())}
for name in [manifest_path, mapping_prefix + 'target-map.json', mapping_prefix + 'seal.json', mapping_prefix + 'body-exception-table.json', verifier_path, capture_plan_path, capture_plan['original_capture_plan']['path'], capture_plan['base_capture_plan']['path'], 'verification/swift-semantic-adapter-root-review/dispatch-retained-physical-identity-acceptance.json']:
    tracked[name] = pin(name)
tracked[str(Path(__file__).relative_to(ROOT))] = pin(str(Path(__file__).relative_to(ROOT)))
for name, before in tracked.items():
    assert pin(name) == before, name
write('audit-input-pins.json', {'schema': 1, 'pins': sorted(tracked.values(), key=lambda row: row['path']), 'posthashes_equal': True})
receipt = {
    'schema': 1,
    'status': 'OFFLINE_INTEGRITY_AUDIT_PASSED_REVIEW_SCOPED_LOCAL_FACTS_ONLY',
    'command': ['python3', '-B', 'verification/swift-retained-geometry-independent/audit_review.py'],
    'cwd': str(ROOT),
    'interpreter_information_without_version_probe': sys.version,
    'source146_tree_sha256': SOURCE_TREE,
    'source_members_currently_rehashed': len(source_pins),
    'frozen_geometry_members_rehashed': len(sealed) - 2,
    'whole_native_spans_rechecked': len(whole_spans),
    'source_spans_rechecked': len(targets),
    'saved_debug_record_lines_rechecked': len(debug_by_line),
    'whole_function_global_line_coordinates_rechecked': True,
    'alternate_configuration_exact_argv_text_checked': True,
    'compiler_version_from_saved_pinned_plan_only': capture_plan['version_from_prior_pinned_receipt'],
    'body_exception_table_rechecked': True,
    'raw_anchor_occurrences_rechecked': anchor_count,
    'distinct_raw_anchors_rechecked': len(anchor_distinct),
    'native_and_IR_call_inventory_matches_complete_text': call_inventory,
    'raw_distinct_pair_bytes': sum(row['bytes'] for row in raw_pins.values()),
    'raw_limit_bytes': MAX_RAW,
    'derived_limit_bytes': MAX_DERIVED,
    'raw_pair_copied': False,
    'alarm_seconds': 50,
    'per_command_ceiling_seconds': 55,
    'elapsed_seconds_before_receipt': time.monotonic() - START,
    'compiler_native_tests_model_geometry_verifier_version_or_process_probes': 0,
    'native_capture_or_UI_instances_started': 0,
    'cleanup_owed': False,
    'initial_peer_preliminary_seal_failure_retained': failure,
    'all_reviewed_inputs_rehashed_after': True,
    'numeric_union': None,
    'whole_capacity': None,
    'physical_alignment': None,
    'runtime_admission': 'WholeQuotePending',
    'original_capture_qualified': False,
    'complete_capacity_prices_root_funding_product_or_GA_accepted': False,
    'limitations': 'Integrity and independent manual local-facts review only. No certificate/verifier result, physical congruence, upstream O arena, external backing/callee/unwind capacity, runtime admission, or original-build qualification.',
}
write('audit-receipt.json', receipt)
assert sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file()) < MAX_DERIVED
print(json.dumps({'status': receipt['status'], 'sealed_members': receipt['frozen_geometry_members_rehashed'], 'source_members': len(source_pins), 'whole_native_spans': len(whole_spans), 'anchors': anchor_count, 'elapsed_seconds': time.monotonic() - START}, sort_keys=True))
