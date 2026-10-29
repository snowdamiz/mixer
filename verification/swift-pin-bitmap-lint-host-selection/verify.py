#!/usr/bin/env python3
"""Read-only guarded source/installed-workflow verification, never host execution."""
import unittest.mock
import offline
offline.install()
import argparse
import ast
import difflib
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import sys
import admit as a
import bounded_commands as b

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
ORIGINAL = HERE.parent / 'swift-pin-bitmap-lint-independent-admission'
CORRECTION = HERE.parent / 'swift-pin-bitmap-lint-host-evidence-correction'
WORKFLOW_SHA256 = 'd7af6cff1238e02982be50dbd27634a15119a626128549409d9d278c0465625e'
RUNTIME_NAMES = {'host-controls-result.json', 'controls-result.json', 'test-output.txt'}


def row(path):
    raw = b.regular(path).read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def tree(rows):
    return hashlib.sha256(''.join(n + '\0' + rows[n]['sha256'] + '\n'
                                  for n in sorted(rows)).encode()).hexdigest()


def packet(path, expected_sha, expected_members, expected_tree):
    assert row(path / 'seal.json')['sha256'] == expected_sha, 'Frozen seal mismatch'
    seal = b.json_data((path / 'seal.json').read_bytes())
    assert len(seal['files']) == expected_members and seal['treeSHA256'] == expected_tree
    for name, expected in seal['files'].items():
        assert row(path / b.member(name)) == expected, 'Frozen member mismatch: ' + name
    assert tree(seal['files']) == expected_tree, 'Frozen tree mismatch'


def source_tests(text):
    module = ast.parse(text)
    cls = next(n for n in module.body if isinstance(n, ast.ClassDef) and n.name == 'Controls')
    return {n.name: ast.get_source_segment(text, n) for n in cls.body
            if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')}


def check(*, verify_seal=True, installed_workflow=False):
    for actual in (b.subprocess.Popen, os.waitpid, os.setsid, os.killpg,
                   signal.setitimer, socket.socket, b.resource.getrusage):
        assert actual is offline.denied
    assert sys.dont_write_bytecode and offline.HERE == HERE
    packet(ORIGINAL, '2012b4f0aabe97ebc2c10a501ea0f1dcc06791b0b4dcc5db5bb80c371fb28238',
           18, 'b3bb8c60d2a14213b48e7a203b97618cce8214fd78b09219f9d779fd3ef7359c')
    packet(CORRECTION, '2512656148042b14810b123aae2e85bbed5ee13b0c877e2cd212c7bc7d7c7f1d',
           12, 'edf5569105e6ec5e6672a2c07635c66ac7d1681b4e8dccab4c8b14fb18612d30')
    packet(HERE.parent / 'swift-pin-bitmap-lint-host-proposal-review',
           '16b9a002222f2df7e2977d9cd90b441f066d7f982f529133e0abb1483e8383f9',
           7, 'a45be44c06a4c7e3c27df9a91db545bc94b5339d39f66dde5aabc41df6c71223')
    for name in ('admit.py', 'bounded_commands.py', 'offline.py', 'controls.py'):
        assert (HERE / name).read_bytes() == (CORRECTION / name).read_bytes(), 'Copied code drift'

    basis = b.json_data((HERE / 'source-basis.json').read_bytes())
    assert basis['parentSuppliedRevision'] == '6d57e05e58e6d614e58a0a4dc0fad661264fb46f'
    assert basis['parentSuppliedGitTree'] == '8d7444955c4e6f2519b6e0823d52f131d180a1af'
    assert basis['GitVerified'] is False
    for name, bound in basis['copiedCode'].items():
        assert row(HERE / name) == {k: bound[k] for k in ('bytes', 'sha256')}
    old = (ORIGINAL / 'host_controls.py').read_text()
    new = (HERE / 'host_controls.py').read_text()
    before, after = source_tests(old), source_tests(new)
    assert set(before) == set(after) and len(after) == 27
    assert [n for n in before if before[n] != after[n]] == ['test_workflow_no_node_install_and_exact_scope']
    assert len(source_tests((HERE / 'controls.py').read_text())) == 16
    # No module/helper/import or other class body changes may hide behind the
    # documented single workflow-location assertion adaptation.
    assert new.replace(after['test_workflow_no_node_install_and_exact_scope'],
                       before['test_workflow_no_node_install_and_exact_scope'], 1) == old
    for name, before_text in (
        ('host_controls.py', old),
        ('workflow.yml', (ORIGINAL / 'workflow.yml').read_text()),
        ('reuse.json', (ORIGINAL / 'reuse.json').read_text()),
    ):
        expected_diff = ''.join(difflib.unified_diff(before_text.splitlines(keepends=True),
                         (HERE / name).read_text().splitlines(keepends=True),
                         fromfile='frozen/' + name, tofile='selected/' + name))
        assert (HERE / (name + '.diff')).read_text() == expected_diff
    reuse = b.json_data((HERE / 'reuse.json').read_bytes())
    original_reuse = b.json_data((ORIGINAL / 'reuse.json').read_bytes())
    assert reuse['genericPreimage'] == {
        'path': 'verification/swift-pin-bitmap-lint-host-evidence-correction/admit.py',
        'sha256': 'd477eeabdfc08f629a3782e306958ea4c5db6102a680d30296e0211335693302'}
    assert {k: v for k, v in reuse.items() if k != 'genericPreimage'} == {
        k: v for k, v in original_reuse.items() if k != 'genericPreimage'}
    assert len(reuse['genericFunctions']) == 9

    manifest, data = a.inputs()
    assert len(data) == 136 and len(a.OVERLAYS) == 15
    assert a.closure(manifest['candidateFiles']) == '7f188bd7b0fe12244936bcbde3f1e4b2f9d9d3fedd43cacbf750d4ba55684748'
    assert (a.ACTIVE_SECONDS, a.CLEANUP_SECONDS, b.MAX_COMMANDS,
            b.OUTPUT_CAP, b.AGGREGATE_OUTPUT_CAP) == (1800, 60, 6, 8388608, 33554432)
    paths = {n: Path('$RUNNER_TEMP/pin-bitmap-lint-regression-v1-evidence/scratch') / n
             for n in ('source', 'target', 'cargo', 'home', 'nodebin')}
    plan = a.command_plan(paths, Path('$RUSTUP_HOME/toolchains') / a.TOOLCHAIN / 'bin',
                         Path('$RUNNER_TEMP/pin-bitmap-lint-regression-v1-evidence/scratch/rustfmt.toml'),
                         {'path': '$NODE_REALPATH'})
    assert json.loads(json.dumps(plan)) == b.json_data((ORIGINAL / 'command-plan.json').read_bytes())['commands']
    assert row(HERE / 'workflow.yml')['sha256'] == WORKFLOW_SHA256
    assert basis['workflow']['proposed'] == row(HERE / 'workflow.yml')
    if installed_workflow:
        assert row(ROOT / a.WORKFLOW_PATH)['sha256'] == WORKFLOW_SHA256, 'Installed workflow differs from proposal'

    if verify_seal:
        seal = b.json_data((HERE / 'seal.json').read_bytes())
        for name, expected in seal['files'].items():
            assert row(HERE / b.member(name)) == expected, 'Selected static packet drift: ' + name
        assert tree(seal['files']) == seal['treeSHA256']
        actual = {p.relative_to(HERE).as_posix() for p in HERE.rglob('*') if p.is_file()
                  and p.name not in RUNTIME_NAMES and p.name != 'seal.json'}
        assert actual == set(seal['files']), 'Unsealed static file present'
    assert not list(HERE.glob('pure-*')) and not list(HERE.rglob('__pycache__'))
    assert offline.ATTEMPTS == []
    return {'schema': 1, 'sourceOnly': True, 'candidateMembers': len(data), 'overlays': len(a.OVERLAYS),
            'candidateTreeSHA256': a.CANDIDATE, 'workflowSHA256': WORKFLOW_SHA256,
            'installedWorkflowChecked': installed_workflow, 'staticSealChecked': verify_seal,
            'originalHostControls': 27, 'unchangedOriginalBodies': 26, 'exactCorrectionControls': 16,
            'runtimeRuns': 0, 'liveApiAttempts': offline.ATTEMPTS,
            'validationScope': 'Guarded file hashes, source AST/body identity and structural workflow source only; no YAML/actionlint validation'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed-workflow', action='store_true',
                        help='Also require canonical installed workflow to match the proposed SHA256 exactly')
    args = parser.parse_args()
    print(json.dumps(check(installed_workflow=args.installed_workflow), sort_keys=True))
