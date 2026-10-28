"""One-shot stdlib validation/freeze of contract documents, never a verifier run."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import stat
import time

ROOT = Path('/Users/andreyyurlov/Documents/dev/mixer')
OUT = ROOT / 'verification/swift-retained-stage-verifier-contract-v1'
LIMIT_SECONDS = 55
MAX_FILE = 2 * 1024 * 1024
MAX_READ = 8 * 1024 * 1024
COMMAND = ('/opt/homebrew/Cellar/python@3.14/3.14.8/Frameworks/Python.framework/'
           'Versions/3.14/bin/python3.14 -B '
           'verification/swift-retained-stage-verifier-contract-v1/prepare_contract.py')
INPUT_NAMES = (
    'AGENTS.md',
    'verification/swift-root-bound-dispatch-retained-verifier-v1/freeze/seal.json',
    'verification/swift-root-bound-dispatch-retained-verifier-v1/source/region_certificate.py',
    'verification/swift-root-bound-dispatch-retained-verifier-independent/seal.json',
    'verification/swift-semantic-adapter-root-review/dispatch-retained-verifier-source-acceptance.json',
    'verification/swift-semantic-adapter-root-review/dispatch-retained-local-geometry-acceptance.json',
    'verification/swift-retained-geometry-independent/local-facts-review.json',
    'verification/swift-retained-partial-certificate-v1/seal.json',
    'verification/swift-retained-partial-certificate-v1/schema-assessment.json',
    'verification/swift-retained-partial-certificate-v1/proposed-partial-semantic-map.json',
    'verification/swift-retained-partial-certificate-v1/preparation-receipt.json',
)
SOURCE_NAMES = ('README.md', 'contract.json', 'failure-matrix.json', 'prepare_contract.py')
FIXED_HASHES = {
    INPUT_NAMES[1]: '8abb6802e73f98982bf863b16175617ca770a72e264364084aa8fa1c84226ee7',
    INPUT_NAMES[2]: '639a154b47f57481c1b7c2900be1cb67e2d3a7e9fe824b19eac23b4a69f32672',
    INPUT_NAMES[3]: '57f374b75c686fbc62024fd31b2a7ea37e80e33c57016a15b2db99dd3f3b739f',
    INPUT_NAMES[7]: '278095d3c9e615490c6bcc4046589f20f8beff365845d3e41764ea070126c09a',
}
SCOPE = {
    'link_dead_code': True,
    'alternate_diagnostic_configuration_only': True,
    'original_capture_qualified': False,
    'runtime_admission_accepted': False,
    'local_geometry_only': True,
    'complete_capacity_accepted': False,
}


def need(value, message):
    if not value:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def unique(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, 'duplicate JSON key')
        result[key] = value
    return result


def load(raw):
    return json.loads(raw.decode(), object_pairs_hook=unique,
                      parse_constant=lambda _: need(False, 'nonfinite JSON'))


def member(name, raw):
    return {'path': name, 'bytes': len(raw), 'sha256': digest(raw)}


def stable_read(path):
    before = path.lstat()
    need(stat.S_ISREG(before.st_mode) and before.st_size <= MAX_FILE,
         'bounded source/metadata regular file')
    raw = path.read_bytes()
    after = path.lstat()
    identity = lambda value: (value.st_dev, value.st_ino, value.st_size,
                              value.st_mtime_ns, value.st_ctime_ns)
    need(identity(before) == identity(after) and len(raw) == before.st_size,
         'source/metadata changed during read')
    return raw


def save(name, value):
    path = OUT / name
    need(not path.exists(), 'one-shot output already exists: ' + name)
    path.write_bytes(json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode() + b'\n')


started = time.monotonic()
need(not (OUT / 'seal.json').exists(), 'frozen contract is not rewritten')
inputs = {name: stable_read(ROOT / name) for name in INPUT_NAMES}
sources = {name: stable_read(OUT / name) for name in SOURCE_NAMES}
need(sum(map(len, inputs.values())) + sum(map(len, sources.values())) <= MAX_READ,
     'aggregate source/metadata read budget')
for name, expected in FIXED_HASHES.items():
    need(digest(inputs[name]) == expected, 'selected immutable source/metadata digest')

assessment = load(inputs[INPUT_NAMES[8]])
lines = inputs[INPUT_NAMES[2]].splitlines(keepends=True)
need(len(assessment['findings']) == 7, 'seven selected grammar findings')
for row in assessment['findings']:
    span = row['source']
    need(span['path'] == INPUT_NAMES[2], 'grammar source identity')
    selected = b''.join(lines[span['line_begin'] - 1:span['line_end_inclusive']])
    need(digest(selected) == span['sha256_of_selected_lines'], 'grammar source span digest')

contract = load(sources['contract.json'])
matrix = load(sources['failure-matrix.json'])
need(contract['scope'] == SCOPE and all(type(value) is bool for value in SCOPE.values()),
     'fixed retained diagnostic scope')
need(contract['base_verifier_source_sha256'] == FIXED_HASHES[INPUT_NAMES[2]], 'base source join')
need(contract['execution']['implementation_authorized'] is False and
     contract['execution']['actual_input_invocation_selected'] is False and
     contract['execution']['actual_certificate_emitted'] is False and
     contract['execution']['actual_inventory_or_semantic_or_root_approval_emitted'] is False,
     'no implementation/certificate/invocation authority')
for name, definition in contract['closed_types'].items():
    need(set(definition) == {'fields', 'types'}, 'closed descriptor schema: ' + name)
    need(type(definition['fields']) is list and
         len(definition['fields']) == len(set(definition['fields'])) and
         set(definition['fields']) == set(definition['types']), 'exact fields/types: ' + name)
    need(all(type(value) is str and value for value in definition['types'].values()),
         'nonempty descriptor types: ' + name)
for name, values in contract['enums'].items():
    need(len(values) == len({canonical(value) for value in values}), 'unique enum: ' + name)
for name in ('certificate', 'semantic_review', 'root_approval'):
    need(contract['envelope_changes'][name]['schema'] == 2, 'distinct v2 envelope')
for name in ('semantic_review', 'root_approval'):
    fields = (contract['envelope_changes'][name]['old_closed_fields_preserved'] +
              contract['envelope_changes'][name]['added_closed_fields'])
    need(len(fields) == len(set(fields)), 'disjoint envelope extension')
need(contract['closed_types']['storage_stages']['fields'] ==
     ['schema', 'inventory_sha256', 'reviewed_complete', 'objects', 'stages', 'copies'],
     'single closed additive stage object')
need(contract['bounds']['MAX_FILES'] == 192 and
     contract['bounds']['MAX_TOTAL_BYTES'] == 335544320 and
     contract['bounds']['MAX_JSON_BYTES_PER_ARTIFACT'] == 2097152 and
     contract['bounds']['MAX_AGGREGATE_ANCHOR_HASH_BYTES'] == 536870912,
     'old artifact budgets unchanged')
need(all(type(value) is int and value > 0 for name, value in contract['bounds'].items()
         if name.startswith('MAX_')), 'positive finite new bounds')
cases = matrix['cases']
need(len(cases) == len({row['id'] for row in cases}), 'unique required control IDs')
need(all(row['expect'] in matrix['outcomes'] for row in cases), 'unambiguous control outcomes')
need(len(cases) >= 42 and {'T13', 'T14', 'T24', 'T27b', 'T36', 'T40'} <=
     {row['id'] for row in cases}, 'stage/alias/unwind/initialization/union controls')
for name, raw in inputs.items():
    need(stable_read(ROOT / name) == raw, 'metadata posthash unchanged')
for name, raw in sources.items():
    need(stable_read(OUT / name) == raw, 'contract source posthash unchanged')
need(time.monotonic() - started < LIMIT_SECONDS, 'bounded source-only validation')

source_members = [member(name, sources[name]) for name in sorted(sources)]
save('source-inputs.json', {
    'schema': 1,
    'status': 'SOURCE_AND_METADATA_PINS_ONLY_NOT_CAPTURE_FACT_OR_INVENTORY_APPROVAL',
    'source146_tree_sha256': '91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f',
    'source_contract_members': source_members,
    'source_contract_tree_sha256': digest(canonical(source_members)),
    'inputs': [member(name, inputs[name]) for name in sorted(inputs)],
    'raw_IR_ASM_MIR_or_source146_member_contents_read': 0,
    'actual_certificate_or_inventory_created': False,
})
tool = load(inputs[INPUT_NAMES[10]])['tool_version_provenance']
log = ('PASS: closed field/type catalogs, bounds, scope/version joins, seven pinned grammar spans, '
       f'{len(cases)} unambiguous deferred controls, unchanged metadata/source posthash.\n'
       'NOT RUN: verifier import/invocation, synthetic verifier controls, actual inputs, compiler/native/UI/network/process probes.\n')
log_path = OUT / 'validation.stdout'
need(not log_path.exists(), 'one-shot validation log')
log_path.write_text(log)
save('preparation-receipt.json', {
    'schema': 1,
    'at': datetime.now(timezone.utc).isoformat(),
    'status': 'SOURCE_ONLY_CONTRACT_VALIDATION_AND_FREEZE_EXACT_ROOT_REVIEW_PENDING',
    'command': COMMAND,
    'scope': SCOPE,
    'tool_version_provenance': {
        'source': INPUT_NAMES[10] + '#tool_version_provenance',
        'version': tool['version'],
        'new_version_probe': False,
    },
    'source146_tree_sha256': '91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f',
    'contract_source_tree_sha256': digest(canonical(source_members)),
    'metadata_read_bytes': sum(map(len, inputs.values())),
    'grammar_source_spans_rehashed': 7,
    'closed_type_definitions_checked': len(contract['closed_types']),
    'future_synthetic_control_cases_defined_not_executed': len(cases),
    'input_metadata_and_contract_source_posthash_unchanged': True,
    'elapsed_seconds_before_finalization': time.monotonic() - started,
    'bounds': {'wall_seconds': LIMIT_SECONDS, 'metadata_bytes': MAX_READ},
    'verifier_import_or_invocation_count': 0,
    'raw_IR_ASM_MIR_or_source146_member_contents_read': 0,
    'actual_fact_verification_or_runtime_checks': 0,
    'actual_certificate_inventory_semantic_or_root_approval_emitted': False,
    'implementation_or_actual_input_invocation_selected': False,
    'compiler_native_UI_network_Docker_database_or_process_probes': False,
    'existing_packet_canonical_metadata_Git_index_or_memory_writes': False,
    'native_instance_or_capture_started': False,
    'cleanup': 'No runtime/capture instance or scratch created; no runtime cleanup owed.',
    'device_runtime_checks': 'Paused/unrun and pending; other project processes preserved.',
    'validation_output': log,
})
names = sorted((*SOURCE_NAMES, 'source-inputs.json', 'validation.stdout', 'preparation-receipt.json'))
members = [member(name, stable_read(OUT / name)) for name in names]
save('seal.json', {
    'schema': 1,
    'status': 'FROZEN_PROPOSED_SOURCE_ONLY_CONTRACT_ROOT_EXACT_REVIEW_PENDING',
    'members': members,
    'tree_sha256': digest(canonical(members)),
    'implementation_or_actual_invocation_authorized': False,
    **SCOPE,
})
print(log, end='')
print('Sealed contract:', digest((OUT / 'seal.json').read_bytes()))
