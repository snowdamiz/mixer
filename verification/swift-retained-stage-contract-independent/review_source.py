"""Bounded one-shot document/source review; no verifier import or invocation."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import stat
import sys
import time

ROOT = Path('/Users/andreyyurlov/Documents/dev/mixer')
OUT = ROOT / 'verification/swift-retained-stage-contract-independent'
PACKET = 'verification/swift-retained-stage-verifier-contract-v1/'
BASE = 'verification/swift-root-bound-dispatch-retained-verifier-v1/'
EXPECTED = {
    PACKET + 'seal.json': '19532e82c9ea9fac5a5edd5dccc5d081d05f2c5fdec2da1689029de0b0b18837',
    BASE + 'freeze/seal.json': '8abb6802e73f98982bf863b16175617ca770a72e264364084aa8fa1c84226ee7',
    BASE + 'source/region_certificate.py': '639a154b47f57481c1b7c2900be1cb67e2d3a7e9fe824b19eac23b4a69f32672',
    'verification/swift-root-bound-dispatch-retained-verifier-independent/seal.json': '57f374b75c686fbc62024fd31b2a7ea37e80e33c57016a15b2db99dd3f3b739f',
    'verification/swift-retained-partial-certificate-v1/seal.json': '278095d3c9e615490c6bcc4046589f20f8beff365845d3e41764ea070126c09a',
}
OTHER = (
    'AGENTS.md',
    'verification/swift-retained-partial-certificate-v1/schema-assessment.json',
    'verification/swift-semantic-adapter-root-review/dispatch-retained-stage-schema-gap.json',
    'verification/swift-semantic-adapter-root-review/dispatch-retained-verifier-source-acceptance.json',
    'verification/swift-semantic-adapter-root-review/dispatch-retained-local-geometry-acceptance.json',
)


def need(value, message):
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def unique(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, 'duplicate key')
        result[key] = value
    return result


def load(raw):
    return json.loads(raw.decode(), object_pairs_hook=unique,
                      parse_constant=lambda _: need(False, 'nonfinite JSON'))


def read(name):
    path = ROOT / name
    first = path.lstat()
    need(stat.S_ISREG(first.st_mode) and first.st_size <= 2 * 1024 * 1024,
         'bounded regular document/source')
    raw = path.read_bytes()
    last = path.lstat()
    identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    need(identity(first) == identity(last) and len(raw) == first.st_size, 'read changed')
    return raw


def member(name, raw):
    return {'path': name, 'bytes': len(raw), 'sha256': sha(raw)}


def save(name, value):
    path = OUT / name
    need(not path.exists(), 'immutable review output exists')
    path.write_bytes(json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode() + b'\n')


started = time.monotonic()
need(not (OUT / 'seal.json').exists(), 'review already frozen')
inputs = {name: read(name) for name in (*EXPECTED, *OTHER)}
for name, expected in EXPECTED.items():
    need(sha(inputs[name]) == expected, 'selected source/seal hash: ' + name)
packet_seal = load(inputs[PACKET + 'seal.json'])
for row in packet_seal['members']:
    name = row['path']
    need('/' not in name and name not in ('.', '..'), 'packet flat member')
    raw = read(PACKET + name)
    inputs[PACKET + name] = raw
    need(member(name, raw) == row, 'frozen contract member: ' + name)
need(sha(canonical(packet_seal['members'])) == packet_seal['tree_sha256'], 'packet tree')
need(sum(map(len, inputs.values())) <= 8 * 1024 * 1024, 'aggregate document budget')

contract = load(inputs[PACKET + 'contract.json'])
matrix = load(inputs[PACKET + 'failure-matrix.json'])
need(len(matrix['cases']) == 46 and len({row['id'] for row in matrix['cases']}) == 46,
     'all 46 deferred controls read')
need(contract['base_verifier_source_sha256'] == EXPECTED[BASE + 'source/region_certificate.py'],
     'immutable base source join')
need(contract['closed_types']['storage_copy']['types']['bytes'] == 'integer 1..U64 or null unknown',
     'F2 nullable copy extent source')
need('length equals twice storage_copy.bytes' in
     contract['closed_types']['copy_source.literal']['types']['bytes_hex'], 'F2 unconditional equality')
need(any('null extent remains missing, never inferred' in row for row in contract['cross_field_rules']),
     'F2 known-only comparison rule')
need(any(row.startswith('Independently reviewed paths are exhaustive mutually exclusive alternatives.')
         for row in contract['cross_field_rules']), 'F1 unconditional exhaustiveness')
need('boolean' == contract['closed_types']['storage_inventory']['types']['inventory_complete'],
     'F1 partial inventory state')
t30 = next(row for row in matrix['cases'] if row['id'] == 'T30')
need(t30['expect'] == 'local_missing' and 'reservation does not close over operation' in t30['mutation'],
     'F3 reservation outcome distinction absent')

assessment = load(inputs['verification/swift-retained-partial-certificate-v1/schema-assessment.json'])
base_lines = inputs[BASE + 'source/region_certificate.py'].splitlines(keepends=True)
need(len(assessment['findings']) == 7, 'seven grammar findings')
for finding in assessment['findings']:
    span = finding['source']
    need(span['path'] == BASE + 'source/region_certificate.py', 'grammar source path')
    raw = b''.join(base_lines[span['line_begin'] - 1:span['line_end_inclusive']])
    need(sha(raw) == span['sha256_of_selected_lines'], 'grammar source span hash')

span_specs = {
    'F1': [('contract.json', 103, 104), ('contract.json', 183, 189),
           ('README.md', 71, 88), ('failure-matrix.json', 20, 22)],
    'F2': [('contract.json', 174, 180), ('contract.json', 195, 195),
           ('failure-matrix.json', 41, 42)],
    'F3': [('README.md', 223, 229), ('README.md', 242, 248),
           ('contract.json', 193, 198), ('failure-matrix.json', 43, 43)],
}
findings = []
for finding_id, specs in span_specs.items():
    spans = []
    for name, begin, end in specs:
        raw = b''.join(inputs[PACKET + name].splitlines(keepends=True)[begin - 1:end])
        spans.append({'path': PACKET + name, 'line_begin': begin,
                      'line_end_inclusive': end, 'sha256_of_selected_lines': sha(raw)})
    findings.append({'id': finding_id, 'source_spans': spans,
                     'amendment': 'Exact normative text and controls in README.md#' + finding_id.lower()})
for name, raw in inputs.items():
    need(read(name) == raw, 'source/document posthash unchanged')
need(time.monotonic() - started < 55, '55-second bounded source-only check')

source_members = [member(name, raw) for name, raw in sorted(inputs.items())]
save('review.json', {
    'schema': 1,
    'verdict': 'AMENDMENT_REQUIRED_NO_DEPENDENT_IMPLEMENTATION',
    'findings': findings,
    'reviewed_contract_seal_sha256': EXPECTED[PACKET + 'seal.json'],
    'reviewed_source_members': source_members,
    'reviewed_source_tree_sha256': sha(canonical(source_members)),
    'unknowns_required_to_remain_unknown': ['O', 'physical congruences', 'Body nonlocal unwind',
                                           'backing capacities and final destruction',
                                           'runtime/original capture/GA'],
    'unchanged_numeric_union_and_all_or_null_interface_required': True,
    'source_and_document_posthash_unchanged': True,
})
log = ('PASS: exact contract seal/members and immutable verifier/independent/gap pins; '
       'seven grammar-source spans; all 46 deferred control descriptions; '
       'three document findings retained; source/document posthash unchanged.\n'
       'NOT RUN: verifier import/invocation, synthetic verifier tests, actual inputs, '
       'compiler/native/UI/network/Docker/PG/process probes.\n')
(OUT / 'review.stdout').write_text(log)
save('receipt.json', {
    'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'command': sys.executable + ' -B verification/swift-retained-stage-contract-independent/review_source.py',
    'tool_version': sys.version,
    'status': 'SOURCE_ONLY_INDEPENDENT_DOCUMENT_REVIEW_AMENDMENT_REQUIRED',
    'bounds': {'wall_seconds': 55, 'aggregate_read_bytes': 8 * 1024 * 1024},
    'elapsed_seconds': time.monotonic() - started,
    'source_revision': 'Exact sealed document/source hashes; no Git probe',
    'reviewed_source_tree_sha256': sha(canonical(source_members)),
    'read_bytes': sum(map(len, inputs.values())),
    'deferred_controls_read_not_executed': 46,
    'verifier_import_or_invocation_count': 0,
    'raw_native_output_or_source146_member_contents_read': 0,
    'actual_inventory_map_certificate_or_approval_emitted': False,
    'implementation_or_actual_invocation_selected': False,
    'compiler_native_UI_network_Docker_PG_or_process_probe': False,
    'canonical_metadata_Git_index_or_memory_writes': False,
    'scope': {'link_dead_code': True, 'alternate_diagnostic_configuration_only': True,
              'original_capture_qualified': False, 'runtime_admission_accepted': False,
              'local_geometry_only': True, 'complete_capacity_accepted': False},
    'cleanup': 'No runtime/capture instance or scratch created; no cleanup owed.',
    'native_device_runtime_checks': 'Paused/unrun and pending; other project processes preserved.',
    'output': log,
})
names = ['README.md', 'review_source.py', 'review.json', 'receipt.json', 'review.stdout']
members = [member(name, read('verification/swift-retained-stage-contract-independent/' + name))
           for name in sorted(names)]
save('seal.json', {'schema': 1, 'status': 'FROZEN_INDEPENDENT_CONTRACT_REVIEW_AMENDMENT_REQUIRED',
                   'members': members, 'tree_sha256': sha(canonical(members)),
                   'dependent_implementation_accepted': False,
                   'actual_inventory_semantic_root_or_runtime_approval': False})
print(log, end='')
print('Independent review seal SHA-256: ' + sha((OUT / 'seal.json').read_bytes()))
