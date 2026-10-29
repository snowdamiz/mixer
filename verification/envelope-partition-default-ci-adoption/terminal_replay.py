"""Filesystem terminal replay reused from the accepted corrected diagnostic source.

Only adaptation: replay receives the fixture directory directly (no bundle/fixture).
No child, compiler or product is launched by this helper.
"""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
PRODUCER = 'verification/envelope-producer-timeout-experiment'


def need(value, label):
    if not value: raise RuntimeError(label)


def raw(path):
    for part in [*reversed(path.parents), path]:
        need(not part.is_symlink(), 'Symlink refused: ' + str(part))
    need(path.is_file(), 'Regular file required: ' + str(path))
    return path.read_bytes()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def replay(out, admission, module):
    fixture = out
    receipt = json.loads(raw(fixture / 'receipt.json'))
    need(receipt['status'] == 'passed-host-fixture-check' and receipt['errors'] == [], 'Fixture failed or incomplete')
    need(receipt.get('active_checks_completed') is True, 'Active checks incomplete')
    for key in ('revision_before', 'revision_after'):
        need(receipt[key] == admission['revision'], 'Receipt revision differs')
    need(receipt['git_tree_before'] == receipt['git_tree_after'] and re.fullmatch('[0-9a-f]{40}', receipt['git_tree_before']), 'Checkout tree drift')
    need(receipt['runner']['sha256'] == module.sha(ROOT / PRODUCER / 'candidate_runner.py'), 'Executed runner differs')
    need(digest(raw(fixture / 'executed-runner.py')) == receipt['runner']['sha256'], 'Runner snapshot differs')
    module.verify_pack(fixture / 'pack')
    need(receipt['rustc']['sha256'] == admission['compiler_sha256'] and receipt['rustc']['path'] == admission['compiler'], 'Compiler drift')
    module.select_host_target(receipt['rustc']['identity'], json.loads(raw(ROOT / module.PACK / 'inventories/expected-host-layouts.json')))
    expected = json.loads(raw(ROOT / module.PACK / 'inventories/expected-methods.json'))
    names = expected['producer']['names']; groups = module.producer_groups(names)
    wanted = ['revision-before', 'git-tree-before', 'python-version', 'compiler-sysroot-selection', 'rustc-verbose',
              'library-compile', 'producer-compile', 'producer-list']
    wanted += ['producer-' + group['name'] for group in groups]
    wanted += ['independent-compile', 'independent-list', 'independent-execute', 'api-positive']
    api = json.loads(raw(ROOT / module.PACK / 'inventories/expected-api.json'))
    wanted += ['api-negative-' + Path(probe['path']).stem for probe in api['negative']]
    wanted += ['revision-after', 'git-tree-after']
    need(len(wanted) == 40 and [r['name'] for r in receipt['commands']] == wanted, 'Complete ordered 40 commands required')
    total = 0; outputs = {}
    for row in receipt['commands']:
        need(row['child_returned'] and row['owned_group_gone'] and not row['custody_hold'] and not row['timed_out']
             and not row['output_capped'] and not row.get('descendants_outlived_direct_child')
             and row['pipe_eof'] == {'stdout': True, 'stderr': True} and row['errors'] == [], 'Command custody/capture failure')
        need(row['exit'] == (1 if row['name'].startswith('api-negative-') else 0), 'Command exit differs')
        need(row['aggregate_bytes_before'] == total, 'Capture ledger discontinuity')
        for label in ('stdout', 'stderr'):
            info = row[label]; need(info['path'] == 'commands/' + row['name'] + '.' + label, 'Output path differs')
            data = raw(fixture / info['path'])
            need(len(data) == info['bytes'] <= module.OUTPUT_CAP and digest(data) == info['sha256'], 'Output digest/cap differs')
            total += len(data); outputs[(row['name'], label)] = data.decode()
        need(row['aggregate_bytes_after'] == total <= module.TOTAL_OUTPUT_CAP, 'Aggregate capture cap differs')
        need(json.loads(raw(fixture / 'commands' / (row['name'] + '.json'))) == row, 'Command sidecar differs')
    combined = []
    for group in groups:
        text = outputs[('producer-' + group['name'], 'stdout')]
        module.verify_methods(text, group['methods'], True, 78 - len(group['methods'])); combined.append(text)
    text = '\n'.join(combined)
    module.verify_layouts(text, json.loads(raw(ROOT / module.PACK / 'inventories/expected-host-layouts.json')))
    need(re.findall(r'ENVELOPE_ORACLE_CASES=([^\s]+)', text) == ['16170'] and
         re.findall(r'CORRECTED_FINITE_BUDGET_CASES=([^\s]+)', text) == ['5544'], 'Oracle counters differ')
    module.verify_methods(outputs[('independent-execute', 'stdout')], expected['independent_exact_source']['names'], True)
    for lane, key in [('producer', 'producer'), ('independent', 'independent_exact_source')]:
        module.verify_methods(outputs[(lane + '-list', 'stdout')], expected[key]['names'])
        need(receipt['test_binaries'][lane]['executed'] == expected[key]['names'], 'Execution receipt inventory differs')
    for probe in api['negative']:
        name = Path(probe['path']).stem; row = next(r for r in receipt['commands'] if r['name'] == 'api-negative-' + name)
        module.verify_negative(name, outputs[(row['name'], 'stderr')], fixture / 'pack' / probe['path'],
                               fixture / 'scratch' / ('api-negative-' + name), row)
    need(receipt['producer_partition']['complete_disjoint_coverage'] is True, 'Partition closure absent')
    required = {'pack', 'snapshot-observed', 'snapshot', 'runner', 'runner-snapshot', 'python', 'compiler', 'launcher'}
    need(set(receipt['postflight']) == required and all(r['passed'] for r in receipt['postflight'].values()), 'Postflight failed/missing')
    need(receipt['cleanup']['removed'] and receipt['cleanup']['children_and_owned_groups_returned'] and not (fixture / 'scratch').exists(), 'Scratch cleanup incomplete')
    retention = json.loads(raw(fixture / 'retention.json'))
    need(retention['test_files'] == receipt['cleanup']['test_files'] and
         retention['compiler_products'] == receipt['cleanup']['compiler_products'], 'Retention manifest differs')
    for lane in ('producer', 'independent'):
        need(retention['compiler_products'][lane + '-tests']['sha256'] == receipt['test_binaries'][lane]['sha256'], 'Test binary retention identity differs')
    for info in retention['test_files'].values():
        relative = module.member_path(info['path']); data = raw(fixture / relative)
        need(len(data) == info['bytes'] and digest(data) == info['sha256'], 'Retained bytes differ')
    need(all(receipt.get(key) is False for key in module.FLAGS), 'Qualification authority must remain false')
    return {'passed': True, 'commands': 40, 'producer_methods': 78, 'independent_methods': 14,
            'layouts': 32, 'finite_comparisons': 21714, 'output_bytes': total,
            'scope': 'host fixture diagnostic only; independent actual artifact review still required'}
