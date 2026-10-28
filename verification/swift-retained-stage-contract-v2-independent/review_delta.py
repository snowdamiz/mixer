"""Independent bounded checks of frozen document delta; never invoke a verifier."""
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import stat
import sys
import time

ROOT = Path('/Users/andreyyurlov/Documents/dev/mixer')
OUT_NAME = 'verification/swift-retained-stage-contract-v2-independent/'
OUT = ROOT / OUT_NAME
V1 = 'verification/swift-retained-stage-verifier-contract-v1/'
V2 = 'verification/swift-retained-stage-verifier-contract-v2/'
PRIOR = 'verification/swift-retained-stage-contract-independent/'
SEALS = {
    V1: '19532e82c9ea9fac5a5edd5dccc5d081d05f2c5fdec2da1689029de0b0b18837',
    V2: 'f5abac1ca96ee8741e16a9882411c17e9fe9342ab7b0ac76ebfc2c512d5fde82',
    PRIOR: 'df43d958b53785f7928e826d2f7e72c8151ffafb74252f2cdb2a26b03668b5b4',
}


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


def read(name):
    path = ROOT / name
    before = path.lstat()
    need(stat.S_ISREG(before.st_mode) and before.st_size <= 2 * 1024 * 1024,
         'bounded regular document/source')
    raw = path.read_bytes()
    after = path.lstat()
    identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    need(identity(before) == identity(after) and len(raw) == before.st_size, 'unstable read')
    return raw


def member(name, raw):
    return {'path': name, 'bytes': len(raw), 'sha256': digest(raw)}


def save(name, value):
    path = OUT / name
    need(not path.exists(), 'one-shot review output exists')
    path.write_bytes(json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode() + b'\n')


def changed_leaves(left, right, pointer=''):
    need(type(left) is type(right), 'unexpected changed type: ' + pointer)
    if isinstance(left, dict):
        need(left.keys() == right.keys(), 'unexpected changed fields: ' + pointer)
        return sum((changed_leaves(left[k], right[k], pointer + '/' + k) for k in left), [])
    if isinstance(left, list):
        need(len(left) == len(right), 'unexpected changed list length: ' + pointer)
        return sum((changed_leaves(a, b, pointer + '/' + str(i))
                    for i, (a, b) in enumerate(zip(left, right))), [])
    return [] if left == right else [{'pointer': pointer, 'before': left, 'after': right}]


started = time.monotonic()
need(not (OUT / 'seal.json').exists(), 'review already frozen')
inputs = {'AGENTS.md': read('AGENTS.md')}
for prefix, expected in SEALS.items():
    raw = read(prefix + 'seal.json')
    need(digest(raw) == expected, 'selected raw seal digest')
    inputs[prefix + 'seal.json'] = raw
    seal = load(raw)
    need(digest(canonical(seal['members'])) == seal['tree_sha256'], 'sealed member-tree digest')
    names = set()
    for row in seal['members']:
        name = row['path']
        need(type(name) is str and name not in ('', '.', '..') and '/' not in name
             and name not in names, 'unique flat member')
        names.add(name)
        raw = read(prefix + name)
        need(member(name, raw) == row, 'sealed exact member')
        inputs[prefix + name] = raw
need(sum(map(len, inputs.values())) <= 8 * 1024 * 1024, 'aggregate document bound')

binding = load(inputs[V2 + 'input-bindings.json'])
need(binding['v1_contract_seal']['sha256'] == SEALS[V1]
     and binding['independent_review_seal']['sha256'] == SEALS[PRIOR], 'predecessor/review joins')
for row in binding['inputs']:
    need(row['path'] in inputs and member(row['path'], inputs[row['path']]) == row, 'v2 input raw pin')
need(digest(canonical(binding['inputs'])) == binding['input_tree_sha256'], 'v2 input tree')
review = load(inputs[PRIOR + 'review.json'])
need(review['reviewed_contract_seal_sha256'] == SEALS[V1]
     and [r['id'] for r in review['findings']] == ['F1', 'F2', 'F3'], 'predecessor finding authority')
for finding in review['findings']:
    for span in finding['source_spans']:
        raw = b''.join(inputs[span['path']].splitlines(keepends=True)
                       [span['line_begin'] - 1:span['line_end_inclusive']])
        need(digest(raw) == span['sha256_of_selected_lines'], 'predecessor finding exact span')

old = load(inputs[V1 + 'contract.json'])
new = load(inputs[V2 + 'contract.json'])
leaves = changed_leaves(old, new)
need([row['pointer'] for row in leaves] == [
    '/closed_types/copy_source.literal/types/bytes_hex', '/cross_field_rules/5', '/cross_field_rules/12'],
    'exact three changed contract leaves')
need('1..32 exact bytes' in leaves[0]['after']
     and 'when storage_copy.bytes is non-null' in leaves[0]['after']
     and 'when storage_copy.bytes is null, retain that null and emit local missing' in leaves[0]['after'],
     'F2 exact null/known/bound distinction')
need('inventory_complete=true additionally requires' in leaves[1]['after']
     and 'With inventory_complete=false, a supported subset' in leaves[1]['after']
     and 'Listed alternatives must be mutually exclusive.' in leaves[1]['after'],
     'F1 exhaustiveness is conditional; exclusivity remains mandatory')
need('entire half-open operation interval [before,after)' in leaves[2]['after']
     and 'exhaustive known reservation intervals demonstrably fail' in leaves[2]['after']
     and 'known contradiction remains invalid even when some unrelated fact is unknown' in leaves[2]['after'],
     'F3 exact known/unknown distinction')
for name in ('schema', 'bounds', 'enums', 'envelope_changes', 'scope', 'unchanged', 'execution'):
    need(old[name] == new[name], 'unchanged contract authority/schema/bounds: ' + name)
for name in old['closed_types']:
    need(old['closed_types'][name]['fields'] == new['closed_types'][name]['fields'], 'unchanged closed fields')

old_matrix = load(inputs[V1 + 'failure-matrix.json'])
new_matrix = load(inputs[V2 + 'failure-matrix.json'])
need({k: v for k, v in old_matrix.items() if k != 'cases'} ==
     {k: v for k, v in new_matrix.items() if k != 'cases'}, 'unchanged matrix envelope/outcomes')
old_cases = {r['id']: r for r in old_matrix['cases']}
new_cases = {r['id']: r for r in new_matrix['cases']}
extra = ['T10a', 'T10b', 'T28a', 'T29a', 'T29b', 'T30b']
need(len(old_cases) == 46 and len(new_cases) == len(new_matrix['cases']) == 52
     and set(new_cases) - set(old_cases) == set(extra), 'exact six added unique controls')
need([r['id'] for r in new_matrix['cases'] if r['id'] not in extra] ==
     [r['id'] for r in old_matrix['cases']], 'predecessor control order unchanged')
for name, row in old_cases.items():
    if name == 'T30':
        need(changed_leaves(row, new_cases[name])[0]['pointer'] == '/mutation'
             and len(changed_leaves(row, new_cases[name])) == 1, 'T30 mutation only')
        need('coverage cannot be decided' in new_cases[name]['mutation'], 'T30 is unknown coverage')
    else:
        need(row == new_cases[name], 'unchanged predecessor control: ' + name)
need([new_cases[k]['expect'] for k in extra] ==
     ['local_missing', 'invalid', 'local_missing', 'invalid', 'scope_only', 'invalid'], 'six exact outcomes')
need(all(r['expect'] in new_matrix['outcomes'] for r in new_matrix['cases']), 'all outcomes declared')

before_lines = inputs[V1 + 'README.md'].decode().splitlines(keepends=True)
after_lines = inputs[V2 + 'README.md'].decode().splitlines(keepends=True)
opcodes = [q for q in difflib.SequenceMatcher(a=before_lines, b=after_lines, autojunk=False).get_opcodes()
           if q[0] != 'equal']
need(opcodes == [('insert', 13, 13, 13, 20), ('replace', 86, 88, 93, 96),
                 ('replace', 158, 160, 166, 174), ('replace', 215, 216, 229, 233),
                 ('replace', 226, 227, 243, 249)], 'five reviewed README edit groups only')
patch = ''.join(''.join(difflib.unified_diff(inputs[V1 + n].decode().splitlines(keepends=True),
                                          inputs[V2 + n].decode().splitlines(keepends=True),
                                          fromfile=V1 + n, tofile=V2 + n))
                for n in ('README.md', 'contract.json', 'failure-matrix.json')).encode()
need(patch == inputs[V2 + 'source-delta.patch'], 'independently regenerated exact source delta')
for name, raw in inputs.items():
    need(read(name) == raw, 'all input source/document posthash unchanged')
need(time.monotonic() - started < 55, '55-second source-only bound')

members = [member(name, raw) for name, raw in sorted(inputs.items())]
tree = digest(canonical(members))
save('review.json', {
    'schema': 1, 'verdict': 'ACCEPT_EXACT_F1_F2_F3_DOCUMENT_DELTA',
    'new_blockers_found_in_delta': [],
    'reviewed_producer_seal_sha256': SEALS[V2],
    'predecessor_contract_and_review_seals': {V1: SEALS[V1], PRIOR: SEALS[PRIOR]},
    'contract_changed_leaves': leaves,
    'README_changed_opcodes_zero_based_half_open': opcodes,
    'new_control_ids': extra, 'updated_control_ids': ['T30'],
    'deferred_controls_total_not_executed': 52,
    'exact_source_delta_patch_regenerated': True,
    'closed_fields_schemas_enums_bounds_and_all_other_contract_leaves_unchanged': True,
    'scope_binding_union_all_or_null_output_and_actual_unknowns_unchanged': True,
    'input_members': members, 'input_tree_sha256': tree,
    'source_document_posthash_unchanged': True,
    'dependent_implementation_selected': False,
    'actual_inventory_map_certificate_semantic_root_runtime_or_GA_approval': False,
})
log = ('PASS: three exact seals and complete member rosters; v2 input bindings; prior finding spans; '
       'three changed contract leaves; five README edit groups; six added controls and T30-only update; '
       '52 deferred controls; regenerated byte-exact delta; all input posthashes unchanged.\n'
       'VERDICT: accept exact F1/F2/F3 document delta; no new blocker found in delta.\n'
       'NOT RUN: verifier import/invocation, deferred synthetic controls, actual inputs, '
       'compiler/native/UI/network/Docker/database/process probes.\n')
(OUT / 'review.stdout').write_text(log)
save('receipt.json', {
    'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'status': 'SOURCE_ONLY_INDEPENDENT_EXACT_DELTA_ACCEPTED_ROOT_SELECTION_PENDING',
    'command': sys.executable + ' -B ' + OUT_NAME + 'review_delta.py',
    'tool_version': sys.version, 'input_tree_sha256': tree,
    'source_revision': 'Exact sealed source/document tree digest; no Git probe',
    'bounds': {'wall_seconds': 55, 'aggregate_read_bytes': 8 * 1024 * 1024},
    'elapsed_seconds': time.monotonic() - started, 'read_bytes': sum(map(len, inputs.values())),
    'verifier_implementation_import_or_invocation_count': 0,
    'raw_native_output_or_source146_contents_read': 0,
    'canonical_metadata_Git_index_or_memory_writes': False,
    'runtime_capture_UI_network_Docker_database_or_process_probes': False,
    'scope': {'link_dead_code': True, 'alternate_diagnostic_configuration_only': True,
              'original_capture_qualified': False, 'runtime_admission_accepted': False,
              'local_geometry_only': True, 'complete_capacity_accepted': False},
    'native_checks': 'Paused/unrun and pending; other projects preserved.',
    'cleanup': 'No runtime/capture instance or scratch created; no cleanup owed.',
    'output': log,
})
names = ['README.md', 'review_delta.py', 'review.json', 'receipt.json', 'review.stdout']
sealed = [member(name, read(OUT_NAME + name)) for name in sorted(names)]
save('seal.json', {
    'schema': 1, 'status': 'FROZEN_INDEPENDENT_EXACT_F1_F2_F3_DELTA_ACCEPTANCE',
    'members': sealed, 'tree_sha256': digest(canonical(sealed)),
    'reviewed_producer_seal_sha256': SEALS[V2],
    'dependent_implementation_selected': False,
    'actual_inventory_semantic_root_runtime_or_GA_approval': False,
})
print(log, end='')
print('Independent delta review seal SHA-256: ' + digest((OUT / 'seal.json').read_bytes()))
