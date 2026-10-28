"""One-shot source-only F1/F2/F3 document amendment; no verifier implementation."""
from copy import deepcopy
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import stat
import time

ROOT = Path('/Users/andreyyurlov/Documents/dev/mixer')
BASE = ROOT / 'verification/swift-retained-stage-verifier-contract-v1'
REVIEW = ROOT / 'verification/swift-retained-stage-contract-independent'
OUT = ROOT / 'verification/swift-retained-stage-verifier-contract-v2'
BASE_SEAL = '19532e82c9ea9fac5a5edd5dccc5d081d05f2c5fdec2da1689029de0b0b18837'
REVIEW_SEAL = 'df43d958b53785f7928e826d2f7e72c8151ffafb74252f2cdb2a26b03668b5b4'
COMMAND = ('/opt/homebrew/Cellar/python@3.14/3.14.8/Frameworks/Python.framework/'
           'Versions/3.14/bin/python3.14 -B '
           'verification/swift-retained-stage-verifier-contract-v2/prepare_amendment.py')
LIMIT = 55
MAX_READ = 8 * 1024 * 1024
NORMATIVE = ('README.md', 'contract.json', 'failure-matrix.json')


def need(value, reason):
    if not value:
        raise ValueError(reason)


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


def read(path):
    before = path.lstat()
    need(stat.S_ISREG(before.st_mode) and before.st_size <= 2 * 1024 * 1024,
         'bounded regular source/metadata file')
    raw = path.read_bytes()
    after = path.lstat()
    identity = lambda value: (value.st_dev, value.st_ino, value.st_size,
                              value.st_mtime_ns, value.st_ctime_ns)
    need(identity(before) == identity(after) and len(raw) == before.st_size,
         'stable source/metadata read')
    return raw


def pin(path, raw):
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(raw), 'sha256': digest(raw)}


def save_json(name, value):
    path = OUT / name
    need(not path.exists(), 'one-shot output exists: ' + name)
    path.write_bytes(json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode() + b'\n')


def replace_one(value, before, after):
    need(value.count(before) == 1, 'exact amendment preimage')
    return value.replace(before, after, 1)


def verify_packet(directory, expected):
    raw = read(directory / 'seal.json')
    need(digest(raw) == expected, 'selected exact seal')
    packet = load(raw)
    need(packet['tree_sha256'] == digest(canonical(packet['members'])), 'sealed member tree')
    files = {directory / 'seal.json': raw}
    for member in packet['members']:
        name = member['path']
        need(type(name) is str and '/' not in name and name not in ('', '.', '..'),
             'closed sibling member path')
        path = directory / name
        need(path not in files, 'duplicate seal member')
        value = read(path)
        need(len(value) == member['bytes'] and digest(value) == member['sha256'], 'sealed member bytes')
        files[path] = value
    return files


started = time.monotonic()
need(not (OUT / 'seal.json').exists() and all(not (OUT / name).exists() for name in NORMATIVE),
     'new sibling only; do not rewrite frozen docs')
inputs = verify_packet(BASE, BASE_SEAL)
inputs.update(verify_packet(REVIEW, REVIEW_SEAL))
inputs[ROOT / 'AGENTS.md'] = read(ROOT / 'AGENTS.md')
helper_raw = read(OUT / 'prepare_amendment.py')
need(sum(map(len, inputs.values())) + len(helper_raw) <= MAX_READ, 'bounded metadata read')
review = load(inputs[REVIEW / 'review.json'])
need(review['reviewed_contract_seal_sha256'] == BASE_SEAL and
     review['verdict'] == 'AMENDMENT_REQUIRED_NO_DEPENDENT_IMPLEMENTATION', 'review joins')
need([row['id'] for row in review['findings']] == ['F1', 'F2', 'F3'], 'only three selected findings')
for finding in review['findings']:
    for span in finding['source_spans']:
        raw = inputs[ROOT / span['path']]
        selected = b''.join(raw.splitlines(keepends=True)[span['line_begin'] - 1:span['line_end_inclusive']])
        need(digest(selected) == span['sha256_of_selected_lines'], 'reviewed document span')

original = {name: inputs[BASE / name].decode() for name in NORMATIVE}
updated = dict(original)
readme_edits = [
    (
        'true. Otherwise its partial status is required. A partial status never grants\n'
        'complete inventory or complete semantic approval.',
        'true. Otherwise its partial status is required. Partial semantic-review status\n'
        'alone grants neither enumeration completeness nor complete semantic approval.\n'
        'It may bind a separately complete inventory while storage facts remain partial.',
        'F1',
    ),
    (
        'inventory. Each path is a source-reviewed mutually exclusive symbolic\n'
        'alternative through the local frontier, not a runtime-reachability claim. Shared\n',
        'inventory. Every listed path is a source-reviewed symbolic alternative through\n'
        'the local frontier, not a runtime-reachability claim. Listed alternatives must\n'
        'be mutually exclusive. `inventory_complete=true` additionally requires the\n'
        'independently reviewed alternatives to be exhaustive across the required local\n'
        'frontier. With `inventory_complete=false`, a supported subset of alternatives\n'
        'may be retained; omitted or unreviewed alternatives create local missing and\n'
        'never become evidence of exhaustiveness. No fictitious placeholder path is\n'
        'required for an unenumerated alternative. Shared\n',
        'F1',
    ),
    (
        'carry exact lowercase hex bytes, at most 32 bytes, and are permitted only for\n'
        '`store`. External-sret sources carry the corresponding existing outgoing edge\n',
        'carry exact lowercase hex bytes, at most 32 bytes, and are permitted only for\n'
        '`store`. When `storage_copy.bytes` is non-null, the hex length equals twice\n'
        'that byte extent. When it is null, retain the null and emit local missing\n'
        'without inferring extent from the literal; the independent 32-byte literal\n'
        'bound still applies. External-sret sources carry the corresponding existing outgoing edge\n',
        'F2',
    ),
    (
        'Source/destination reservation must cover the whole before/after interval.\n',
        'For each stage endpoint, prove reservation coverage of the entire half-open\n'
        'operation interval `[before,after)` on the exact path. If the exhaustive known\n'
        'reservation intervals demonstrably fail to cover it, the claim is invalid.\n'
        'If an interval, phase, path projection or reservation state is unavailable or\n'
        'partial so that coverage cannot be decided, emit local missing. A supported\n'
        'known contradiction remains invalid even when some unrelated fact is unknown.\n',
        'F3',
    ),
]
for before, after, _ in readme_edits:
    updated['README.md'] = replace_one(updated['README.md'], before, after)
custody_note = (
    'This v2 sibling applies only F1, F2 and F3 from the independent review sealed\n'
    f'`{REVIEW_SEAL}` to v1 contract seal\n'
    f'`{BASE_SEAL}`.\n'
    'Both predecessor packets remain immutable. `change-scope-receipt.json` and\n'
    '`source-delta.patch` bind the exact amendment scope. This sibling awaits root\n'
    'review of the delta before any dependent implementation is selected.\n\n'
)
updated['README.md'] = replace_one(updated['README.md'], '## Scope and versioning\n',
                                 custody_note + '## Scope and versioning\n')

base_contract = load(original['contract.json'].encode())
expected_contract = deepcopy(base_contract)
literal_before = expected_contract['closed_types']['copy_source.literal']['types']['bytes_hex']
literal_after = ('nonempty lowercase hexadecimal encoding of 1..32 exact bytes; when '
                 'storage_copy.bytes is non-null its length equals twice storage_copy.bytes; '
                 'when storage_copy.bytes is null, retain that null and emit local missing '
                 'without inferring extent from the literal')
path_index = next(i for i, value in enumerate(expected_contract['cross_field_rules'])
                  if value.startswith('Independently reviewed paths are exhaustive'))
path_before = expected_contract['cross_field_rules'][path_index]
path_after = replace_one(
    path_before,
    'Independently reviewed paths are exhaustive mutually exclusive alternatives. ',
    'Every listed path is a source-reviewed symbolic alternative. Listed alternatives must be '
    'mutually exclusive. inventory_complete=true additionally requires the independently reviewed '
    'alternatives to be exhaustive across the required local frontier. With inventory_complete=false, '
    'a supported subset of alternatives may be retained; omitted or unreviewed alternatives create '
    'local missing and never become evidence of exhaustiveness. No fictitious placeholder path is '
    'required for an unenumerated alternative. ',
)
reservation_index = next(i for i, value in enumerate(expected_contract['cross_field_rules'])
                         if value.startswith('Known source/destination copy extents'))
reservation_before = expected_contract['cross_field_rules'][reservation_index]
reservation_after = replace_one(
    reservation_before,
    'Both reservations cover before through after; ',
    'For each stage endpoint, prove reservation coverage of the entire half-open operation interval '
    '[before,after) on the exact path. If the exhaustive known reservation intervals demonstrably '
    'fail to cover it, the claim is invalid. If an interval, phase, path projection or reservation '
    'state is unavailable or partial so that coverage cannot be decided, emit local missing. '
    'A supported known contradiction remains invalid even when some unrelated fact is unknown; ',
)
expected_contract['closed_types']['copy_source.literal']['types']['bytes_hex'] = literal_after
expected_contract['cross_field_rules'][path_index] = path_after
expected_contract['cross_field_rules'][reservation_index] = reservation_after
for before, after in ((literal_before, literal_after), (path_before, path_after),
                      (reservation_before, reservation_after)):
    updated['contract.json'] = replace_one(updated['contract.json'], json.dumps(before), json.dumps(after))
need(load(updated['contract.json'].encode()) == expected_contract, 'only three contract value amendments')
need(base_contract['bounds'] == expected_contract['bounds'] and
     base_contract['enums'] == expected_contract['enums'] and
     base_contract['envelope_changes'] == expected_contract['envelope_changes'], 'schemas/enums/bounds unchanged')
for name, definition in expected_contract['closed_types'].items():
    need(definition['fields'] == base_contract['closed_types'][name]['fields'], 'closed field sets unchanged')
    need(set(definition['fields']) == set(definition['types']), 'exact closed field/type catalog')

base_matrix = load(original['failure-matrix.json'].encode())
extra_after = {
    'T10': [
        {'id': 'T10a', 'mutation': 'Correctly bound partial inventory retains a supported subset of mutually exclusive paths; inventory/map/review/root completion joins are false as applicable.', 'expect': 'local_missing', 'invariant': 'Omitted/unreviewed alternatives never establish exhaustiveness or produce numbers; no placeholder path required.'},
        {'id': 'T10b', 'mutation': 'The same supported path subset claims inventory_complete=true while the exact independent review establishes an omitted required alternative.', 'expect': 'invalid'},
    ],
    'T29': [
        {'id': 'T28a', 'mutation': 'Literal store has valid1..32 exact literal bytes but storage_copy.bytes is null and completeness remains partial.', 'expect': 'local_missing', 'invariant': 'Retain null extent; never infer extent, initialization or value lifetime from literal length.'},
        {'id': 'T29a', 'mutation': 'Literal store has known byte extent whose doubled value disagrees with the valid hex length.', 'expect': 'invalid'},
        {'id': 'T29b', 'mutation': 'Literal store has known matching extent and valid bounded lowercase hex bytes, with all other reviewed facts unchanged.', 'expect': 'scope_only', 'invariant': 'Otherwise unchanged; no initialization or value lifetime inferred.'},
    ],
    'T30': [
        {'id': 'T30b', 'mutation': 'Known exhaustive source or destination reservation intervals demonstrably exclude any portion of the required [before,after) operation interval, including when an unrelated fact is unknown.', 'expect': 'invalid'},
    ],
}
t30_after = ('memcpy nonoverlap is unknown, source/destination reservation coverage cannot be '
             'decided because an interval, phase, exact-path projection or reservation state is '
             'unavailable or partial, or external-sret write completeness is unproved.')
expected_matrix = deepcopy(base_matrix)
expected_cases = []
for row in base_matrix['cases']:
    replacement = deepcopy(row)
    if row['id'] == 'T30':
        replacement['mutation'] = t30_after
        updated['failure-matrix.json'] = replace_one(updated['failure-matrix.json'], json.dumps(row['mutation']), json.dumps(t30_after))
    expected_cases.append(replacement)
    additions = extra_after.get(row['id'], [])
    if additions:
        line = next(line for line in updated['failure-matrix.json'].splitlines(keepends=True)
                    if '"id": "' + row['id'] + '"' in line)
        addition_text = ''.join('    ' + json.dumps(item, ensure_ascii=False) + ',\n' for item in additions)
        updated['failure-matrix.json'] = replace_one(updated['failure-matrix.json'], line, line + addition_text)
        expected_cases.extend(deepcopy(additions))
expected_matrix['cases'] = expected_cases
need(load(updated['failure-matrix.json'].encode()) == expected_matrix, 'only F1/F2/F3 failure matrix changes')
need(len(expected_cases) == 52 and len({row['id'] for row in expected_cases}) == 52, '52 unique deferred controls')
need(all(row['expect'] in expected_matrix['outcomes'] for row in expected_cases), 'unambiguous deferred outcomes')

for path, raw in inputs.items():
    need(read(path) == raw, 'all predecessor/review metadata posthash unchanged')
need(read(OUT / 'prepare_amendment.py') == helper_raw, 'preparation source unchanged')
need(time.monotonic() - started < LIMIT, 'bounded source-only document validation')
for name in NORMATIVE:
    (OUT / name).write_text(updated[name])
delta = ''.join(''.join(difflib.unified_diff(original[name].splitlines(keepends=True),
                                           updated[name].splitlines(keepends=True),
                                           fromfile='verification/swift-retained-stage-verifier-contract-v1/' + name,
                                           tofile='verification/swift-retained-stage-verifier-contract-v2/' + name))
                for name in NORMATIVE)
(OUT / 'source-delta.patch').write_text(delta)
binding = {
    'schema': 1,
    'status': 'EXACT_PREDECESSOR_AND_REQUIRED_AMENDMENT_REVIEW_BINDING_ONLY',
    'v1_contract_seal': pin(BASE / 'seal.json', inputs[BASE / 'seal.json']),
    'independent_review_seal': pin(REVIEW / 'seal.json', inputs[REVIEW / 'seal.json']),
    'independent_review_manifest_member': 'review.json',
    'decision_json_absent_not_required_by_seal': True,
    'findings': ['F1', 'F2', 'F3'],
    'inputs': [pin(path, inputs[path]) for path in sorted(inputs)],
    'input_tree_sha256': digest(canonical([pin(path, inputs[path]) for path in sorted(inputs)])),
    'implementation_or_actual_invocation_authorized': False,
}
save_json('input-bindings.json', binding)
save_json('change-scope-receipt.json', {
    'schema': 1,
    'status': 'EXACT_THREE_DOCUMENT_AMENDMENTS_ROOT_DELTA_REVIEW_PENDING',
    'v1_contract_seal_sha256': BASE_SEAL,
    'independent_review_seal_sha256': REVIEW_SEAL,
    'amendments': [
        {'id': 'F1', 'contract_json_pointer': '/cross_field_rules/' + str(path_index), 'README_changes': 'Guard exhaustive alternatives by inventory_complete; partial review can bind separately complete inventory.', 'new_controls': ['T10a', 'T10b']},
        {'id': 'F2', 'contract_json_pointer': '/closed_types/copy_source.literal/types/bytes_hex', 'README_changes': 'Compare length only for known extent; null remains missing and bounded literal length infers nothing.', 'new_controls': ['T28a', 'T29a', 'T29b']},
        {'id': 'F3', 'contract_json_pointer': '/cross_field_rules/' + str(reservation_index), 'README_changes': 'Known exhaustive reservation contradiction invalid; unavailable/partial coverage missing.', 'updated_controls': ['T30'], 'new_controls': ['T30b']},
    ],
    'custody_only_README_addition': 'Sibling provenance and exact delta review boundary.',
    'unchanged': ['all closed field sets', 'envelope schema versions and fields', 'all enums', 'all numeric/resource bounds', 'all other contract values', 'all other failure cases and outcome definitions', 'retained build/scope and synthetic authority', 'original numeric union and all-or-null output', 'all actual unresolved facts and runtime holds'],
    'predecessor_and_review_bytes_posthash_unchanged': True,
    'source_delta': pin(OUT / 'source-delta.patch', delta.encode()),
    'source_only_validation': 'Exact preimage replacements; semantic JSON deep equality against only three permitted contract values and named matrix delta; unchanged schema/enum/bounds/field catalogs; unique explicit outcomes.',
    'actual_verifier_or_semantic_geometry_checks_executed': False,
})
log = ('PASS: both exact seals/all members and reviewed finding spans; only F1/F2/F3 normative amendments; '
       'unchanged schemas/enums/bounds/closed fields;52 unique deferred controls; predecessor/review posthash unchanged.\n'
       'NOT RUN: verifier import/invocation, implementation, actual inputs, raw native outputs, compiler/native/UI/network/Docker/PG/process probes.\n')
(OUT / 'validation.stdout').write_text(log)
review_receipt = load(inputs[REVIEW / 'receipt.json'])
save_json('preparation-receipt.json', {
    'schema': 1,
    'at': datetime.now(timezone.utc).isoformat(),
    'status': 'SOURCE_ONLY_AMENDED_CONTRACT_FREEZE_ROOT_DELTA_REVIEW_PENDING',
    'command': COMMAND,
    'tool_version_provenance': {'source': str((REVIEW / 'receipt.json').relative_to(ROOT)) + '#tool_version', 'version': review_receipt['tool_version'], 'new_version_probe': False},
    'source_revision': 'Exact sealed document/source hashes; no Git probe',
    'source146_tree_sha256': '91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f',
    'input_tree_sha256': binding['input_tree_sha256'],
    'metadata_read_bytes': sum(map(len, inputs.values())),
    'bounds': {'wall_seconds': LIMIT, 'aggregate_metadata_bytes': MAX_READ},
    'elapsed_seconds_before_finalization': time.monotonic() - started,
    'deferred_controls_defined_not_executed': 52,
    'output': log,
    'scope': expected_contract['scope'],
    'verifier_import_or_invocation_count': 0,
    'actual_certificate_inventory_semantic_or_root_approval_emitted': False,
    'raw_native_output_or_source146_member_contents_read': 0,
    'implementation_or_actual_invocation_selected': False,
    'compiler_native_UI_network_Docker_PG_or_process_probe': False,
    'canonical_metadata_Git_index_memory_or_other_lane_writes': False,
    'predecessor_and_review_metadata_posthash_unchanged': True,
    'native_device_runtime_checks': 'Paused/unrun and pending; no instance started; other project processes preserved.',
    'cleanup': 'No runtime/capture instance or scratch created; no runtime cleanup owed.',
})
names = sorted((*NORMATIVE, 'prepare_amendment.py', 'input-bindings.json', 'change-scope-receipt.json',
                'source-delta.patch', 'validation.stdout', 'preparation-receipt.json'))
members = [{'path': name, 'bytes': len(read(OUT / name)), 'sha256': digest(read(OUT / name))} for name in names]
save_json('seal.json', {
    'schema': 1,
    'status': 'FROZEN_AMENDED_SOURCE_ONLY_CONTRACT_ROOT_DELTA_REVIEW_PENDING',
    'members': members,
    'tree_sha256': digest(canonical(members)),
    'v1_contract_seal_sha256': BASE_SEAL,
    'independent_review_seal_sha256': REVIEW_SEAL,
    'implementation_or_actual_invocation_authorized': False,
    **expected_contract['scope'],
})
print(log, end='')
print('Sealed amended contract:', digest(read(OUT / 'seal.json')))
