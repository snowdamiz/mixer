#!/usr/bin/env python3
"""Thin filesystem-only source admission and terminal replay; never launches children."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = 'verification/envelope-producer-timeout-experiment'
WORKFLOW = '.github/workflows/envelope-partition-diagnostic.yml'


def need(value, label):
    if not value: raise RuntimeError(label)


def raw(path):
    for part in [*reversed(path.parents), path]:
        need(not part.is_symlink(), 'Symlink refused: ' + str(part))
    need(path.is_file(), 'Regular file required: ' + str(path))
    return path.read_bytes()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def subject(root=ROOT):
    spec = importlib.util.spec_from_file_location('reviewed_envelope_subject', root / PRODUCER / 'candidate_runner.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_sources(root=ROOT, installed=False, review_seal=True):
    bindings = json.loads(raw(HERE / 'source-bindings.json'))
    for name, row in bindings['runtime_and_contract_dependencies'].items():
        data = raw(root / name)
        need(len(data) == row['bytes'] and digest(data) == row['sha256'], 'Source differs: ' + name)
    seal = json.loads(raw(root / PRODUCER / 'seal.json'))
    need(digest(canonical(seal['members'])) == seal['tree_sha256'], 'Producer member tree differs')
    need(len(seal['members']) == seal['member_count'] == 12, 'Producer member count differs')
    for row in seal['members']:
        path = Path(row['path'])
        need(not path.is_absolute() and '..' not in path.parts and path.as_posix() == row['path'], 'Producer path differs')
        data = raw(root / PRODUCER / path)
        need(len(data) == row['bytes'] and digest(data) == row['sha256'], 'Producer frozen member differs: ' + str(path))
    overlay = json.loads(raw(root / PRODUCER / 'overlay.json'))
    text = raw(root / overlay['base_path']).decode()
    for change in overlay['changes']:
        need(text.count(change['before']) == 1, 'Overlay anchor differs')
        text = text.replace(change['before'], change['after'])
    need(text.encode() == raw(root / PRODUCER / 'candidate_runner.py'), 'Overlay differs')
    module = subject(root)
    module.verify_pack(root / module.PACK)
    if review_seal:
        local_seal = json.loads(raw(HERE / 'seal.json'))
        rows = local_seal['members']
        need(rows == sorted(rows, key=lambda row: row['path']), 'Review order differs')
        need(len(rows) == len({r['path'] for r in rows}) == local_seal['member_count'], 'Review count differs')
        need(digest(canonical(rows)) == local_seal['tree_sha256'], 'Review tree differs')
        need(sum(r['bytes'] for r in rows) == local_seal['total_bytes'], 'Review byte count differs')
        for row in rows:
            rel = Path(row['path'])
            need(not rel.is_absolute() and '..' not in rel.parts and rel.as_posix() == row['path'], 'Review path differs')
            data = raw(HERE / rel)
            need(len(data) == row['bytes'] and digest(data) == row['sha256'], 'Review source differs: ' + str(rel))
    if installed:
        need(raw(root / WORKFLOW) == raw(HERE / 'workflow-proposal.yml'), 'Installed workflow differs')
    return module


def context(env):
    need(env.get('GITHUB_EVENT_NAME') == 'workflow_dispatch', 'Manual dispatch required')
    need(env.get('GITHUB_REPOSITORY') == 'snowdamiz/mixer', 'Wrong repository')
    need(env.get('GITHUB_RUN_ATTEMPT') == '1', 'One first attempt only; rerun denied')
    need(env.get('RUNNER_OS') == 'macOS' and env.get('RUNNER_ARCH') == 'ARM64', 'Fresh hosted macOS ARM64 required')
    need(env.get('MIXER_RUNNER_ENVIRONMENT') == 'github-hosted', 'Fresh GitHub-hosted runner required')
    revision = env.get('MIXER_REVIEWED_SHA', '')
    need(re.fullmatch('[0-9a-f]{40}', revision) is not None and env.get('GITHUB_SHA') == revision, 'Exact reviewed commit required')
    need(re.fullmatch('[0-9]+', env.get('GITHUB_RUN_ID', '')) is not None, 'Malformed run ID')
    return {'revision': revision, 'run_id': env['GITHUB_RUN_ID'], 'attempt': 1}


def replay(out, admission, module):
    fixture = out / 'fixture'
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('verify', 'begin', 'finish'))
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    # No subject can reach a real process API in admission, replay or source tests.
    import offline_guard
    allowed = args.out if args.phase == 'begin' else (args.out or HERE)
    offline_guard.install(allowed)
    module = verify_sources(installed=args.phase != 'verify')
    if args.phase == 'verify':
        print(json.dumps({'passed': True, 'scope': 'source binding only', 'denied_attempts': offline_guard.DENIED})); return
    admitted = context(os.environ)
    expected_out = Path(os.environ['RUNNER_TEMP']) / ('envelope-partition-' + admitted['run_id'] + '-1')
    need(args.out == expected_out and args.out.is_absolute(), 'Output must be exact fresh run-owned path')
    if args.phase == 'begin':
        need(not args.out.exists() and args.out.parent.is_dir(), 'Fresh output required')
        compiler = Path(os.environ['HOME']) / '.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc'
        module.regular(compiler); need(os.access(compiler, os.X_OK), 'Existing direct compiler missing; no installer/fallback')
        admitted.update(compiler=str(compiler), compiler_sha256=module.sha(compiler),
                        runner_sha256=module.sha(ROOT / PRODUCER / 'candidate_runner.py'),
                        scope='One invocation only; missing or unsupported compiler fails before product compilation')
        args.out.mkdir(exist_ok=False)
        (args.out / 'admission.json').write_text(json.dumps(admitted, sort_keys=True, indent=2) + '\n')
    else:
        previous = json.loads(raw(args.out / 'admission.json'))
        need(all(previous[k] == v for k, v in admitted.items()), 'Admission context drift')
        result = replay(args.out, previous, module)
        (args.out / 'terminal-replay.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    need(offline_guard.DENIED == [], 'Unexpected process attempt')


if __name__ == '__main__':
    main()
