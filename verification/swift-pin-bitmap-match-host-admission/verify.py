#!/usr/bin/env python3
"""Read-only guarded source/workflow verifier; no hosted or product execution."""
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
import re
import signal
import socket
import sys
import admit as a
import bounded_commands as b

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
BASE = HERE.parent / 'swift-pin-bitmap-lint-host-selection'
SOURCE = HERE.parent / 'swift-pin-bitmap-match-binding-correction'
ORIGINAL = HERE.parent / 'swift-pin-bitmap-lint-independent-admission'
REVIEW = HERE.parent / 'swift-pin-bitmap-lint-actual-review'
OLD_SOURCE = 'verification/swift-pin-bitmap-lint-correction'
NEW_SOURCE = 'verification/swift-pin-bitmap-match-binding-correction'
OLD_DRIVER = 'verification/swift-pin-bitmap-lint-host-selection'
NEW_DRIVER = 'verification/swift-pin-bitmap-match-host-admission'
SOURCE_SEAL = '0210ab9c252c6f7a5a3eff077e36c2811c79351d916d78b75b2cda88e2bdf85c'
SOURCE_CLOSURE = 'e9282e05cea70d4aceaf6a145fb9f971acb023dd41a7d4651216753666305ba1'
SOURCE_MEMBERS = 24
RUNTIME_NAMES = {'host-controls-result.json', 'controls-result.json', 'test-output.txt'}


def row(path):
    raw = b.regular(path).read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def tree(rows):
    return hashlib.sha256(''.join(n + '\0' + rows[n]['sha256'] + '\n'
                                  for n in sorted(rows)).encode()).hexdigest()


def packet(path, expected_sha):
    assert row(path / 'seal.json')['sha256'] == expected_sha, 'Frozen seal mismatch'
    seal = b.json_data((path / 'seal.json').read_bytes())
    assert type(seal) is dict and type(seal['files']) is dict
    for name, expected in seal['files'].items():
        assert type(name) is str and type(expected) is dict
        assert set(expected) == {'bytes', 'sha256'}
        assert type(expected['bytes']) is int and expected['bytes'] >= 0
        assert type(expected['sha256']) is str and re.fullmatch('[0-9a-f]{64}', expected['sha256'])
        assert row(path / b.member(name)) == expected, 'Frozen member mismatch: ' + name
    assert tree(seal['files']) == seal['treeSHA256'], 'Frozen tree mismatch'
    return seal


def source_tests(text):
    cls = next(n for n in ast.parse(text).body if isinstance(n, ast.ClassDef) and n.name == 'Controls')
    return {n.name: ast.get_source_segment(text, n) for n in cls.body
            if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')}


def expected_replacements():
    return [
        {'before': "PACKET = ROOT / '" + OLD_SOURCE + "'", 'after': "PACKET = ROOT / '" + NEW_SOURCE + "'", 'count': 1},
        {'before': "SEAL_SHA = '89505e8f873e5c225d711f8ae923bd8149db30a74603c49dddb523639cb11052'", 'after': "SEAL_SHA = '" + SOURCE_SEAL + "'", 'count': 1},
        {'before': "CANDIDATE = '7f188bd7b0fe12244936bcbde3f1e4b2f9d9d3fedd43cacbf750d4ba55684748'", 'after': "CANDIDATE = '" + SOURCE_CLOSURE + "'", 'count': 1},
        {'before': "need(len(sealed['files']) == 31, 'Exact 31 sealed input members')", 'after': "need(len(sealed['files']) == 24, 'Exact 24 sealed input members')", 'count': 1},
        {'before': "'" + OLD_SOURCE + "/candidate/vm/'", 'after': "'" + NEW_SOURCE + "/candidate/vm/'", 'count': 1},
    ]


def check(*, verify_seal=True, installed_workflow=False):
    for actual in (b.subprocess.Popen, os.waitpid, os.setsid, os.killpg,
                   signal.setitimer, socket.socket, b.resource.getrusage):
        assert actual is offline.denied
    assert sys.dont_write_bytecode and offline.HERE == HERE
    base_seal = packet(BASE, 'd8368ae3e4287e56b8dff3f0533c50b415a61cc30e20590875d4612c16afe239')
    review_seal = packet(REVIEW, 'ba20b76ea587bf52620908fd1d56a53bbd22d4ab74908abbb71308e4de9ebf47')
    source_seal = packet(SOURCE, SOURCE_SEAL)
    assert len(source_seal['files']) == SOURCE_MEMBERS
    basis = b.json_data((HERE / 'source-basis.json').read_bytes())
    assert basis['parentSuppliedRevision'] == '88c32d7fe9a5596d269ad29eb63c380dc5e820b4'
    assert basis['parentSuppliedGitTree'] == '6bca344641b9b4c9e928a460b801f8c93d2a90ad'
    assert basis['GitVerified'] is False
    for path, seal, sha in ((BASE, base_seal, 'd8368ae3e4287e56b8dff3f0533c50b415a61cc30e20590875d4612c16afe239'),
                            (REVIEW, review_seal, 'ba20b76ea587bf52620908fd1d56a53bbd22d4ab74908abbb71308e4de9ebf47'),
                            (SOURCE, source_seal, SOURCE_SEAL)):
        assert basis['frozenPackets'][path.name] == {'sealSHA256': sha, 'members': len(seal['files']), 'treeSHA256': seal['treeSHA256']}
    assert basis['candidate'] == {'path': NEW_SOURCE, 'members': 136, 'overlays': 15,
                                  'sealedMembers': SOURCE_MEMBERS, 'sealSHA256': SOURCE_SEAL,
                                  'treeSHA256': SOURCE_CLOSURE,
                                  'baselineTreeSHA256': 'af0db424af7b08f013d2c6a8894f4d156f76bc5f493620c6f2c0b85d3bf4c48b',
                                  'materializationPrefix': NEW_SOURCE + '/candidate/vm/'}
    assert basis['admitReplacements'] == expected_replacements()
    rebound = (HERE / 'admit.py').read_text()
    for binding in expected_replacements():
        assert rebound.count(binding['after']) == binding['count']
        rebound = rebound.replace(binding['after'], binding['before'], binding['count'])
    assert rebound == (BASE / 'admit.py').read_text(), 'Unexpected runtime source change'
    for name in ('bounded_commands.py', 'offline.py', 'reuse.json'):
        assert (HERE / name).read_bytes() == (BASE / name).read_bytes()
        assert basis['copiedByteIdentical'][name] == row(HERE / name)
    reuse = b.json_data((HERE / 'reuse.json').read_bytes())
    assert reuse['genericPreimage'] == {
        'path': 'verification/swift-pin-bitmap-lint-host-evidence-correction/admit.py',
        'sha256': 'd477eeabdfc08f629a3782e306958ea4c5db6102a680d30296e0211335693302'}
    assert len(reuse['genericFunctions']) == 9

    old_host, new_host = (BASE / 'host_controls.py').read_text(), (HERE / 'host_controls.py').read_text()
    assert new_host == old_host.replace(OLD_SOURCE, NEW_SOURCE).replace(OLD_DRIVER, NEW_DRIVER)
    before, after = source_tests(old_host), source_tests(new_host)
    assert len(before) == len(after) == 27 and set(before) == set(after)
    assert [n for n in before if before[n] != after[n]] == ['test_workflow_no_node_install_and_exact_scope']
    old_controls, new_controls = (BASE / 'controls.py').read_text(), (HERE / 'controls.py').read_text()
    expected_controls = old_controls.replace(
        "        new = ast.parse((HERE / 'admit.py').read_text())",
        "        rebound = (HERE / 'admit.py').read_text()\n"
        "        bindings = json.loads((HERE / 'source-basis.json').read_text())['admitReplacements']\n"
        "        for binding in bindings:\n"
        "            self.assertEqual(rebound.count(binding['after']), binding['count'])\n"
        "            rebound = rebound.replace(binding['after'], binding['before'], binding['count'])\n"
        "        self.assertEqual(rebound, (HERE.parent / 'swift-pin-bitmap-lint-host-evidence-correction' / 'admit.py').read_text())\n"
        "        new = ast.parse(rebound)", 1).replace(
        "(136, 15, '7f188bd7b0fe12244936bcbde3f1e4b2f9d9d3fedd43cacbf750d4ba55684748')",
        "(136, 15, '" + SOURCE_CLOSURE + "')", 1)
    assert new_controls == expected_controls
    before, after = source_tests(old_controls), source_tests(new_controls)
    assert len(before) == len(after) == 16 and set(before) == set(after)
    assert [n for n in before if before[n] != after[n]] == basis['correctionControlChanges']
    assert basis['controlsPreserved'] == {'hostUnchangedBodies': 26, 'correctionUnchangedBodies': 14, 'noAssertionsRemoved': True}
    for name in ('admit.py', 'host_controls.py', 'controls.py', 'workflow.yml'):
        expected_diff = ''.join(difflib.unified_diff((BASE / name).read_text().splitlines(keepends=True),
                         (HERE / name).read_text().splitlines(keepends=True),
                         fromfile='accepted/' + name, tofile='rebound/' + name))
        assert (HERE / (name + '.diff')).read_text() == expected_diff

    manifest, data = a.inputs()
    assert type(manifest) is dict
    for key in ('baselineFiles', 'candidateFiles', 'materializationPaths'):
        assert type(manifest[key]) is dict and len(manifest[key]) == 136
    assert type(manifest['overlayPaths']) is list and manifest['overlayPaths'] == list(a.OVERLAYS)
    assert set(manifest['baselineFiles']) == set(manifest['candidateFiles']) == set(manifest['materializationPaths'])
    for name in manifest['candidateFiles']:
        assert type(name) is str and b.member(name).as_posix() == name
        for key in ('baselineFiles', 'candidateFiles'):
            expected = manifest[key][name]
            assert type(expected) is dict and set(expected) == {'bytes', 'sha256'}
            assert type(expected['bytes']) is int and 0 <= expected['bytes'] <= a.MAX_FILE_BYTES
            assert type(expected['sha256']) is str and re.fullmatch('[0-9a-f]{64}', expected['sha256'])
        expected_path = (NEW_SOURCE + '/candidate/vm/' if name in a.OVERLAYS else 'vm/') + name
        assert type(manifest['materializationPaths'][name]) is str
        assert manifest['materializationPaths'][name] == expected_path
    assert len(data) == 136 and len(a.OVERLAYS) == 15
    assert a.closure(manifest['baselineFiles']) == a.BASELINE == 'af0db424af7b08f013d2c6a8894f4d156f76bc5f493620c6f2c0b85d3bf4c48b'
    assert a.closure(manifest['candidateFiles']) == a.CANDIDATE == SOURCE_CLOSURE
    assert a.PACKET == SOURCE and a.SEAL_SHA == SOURCE_SEAL
    assert (a.ACTIVE_SECONDS, a.CLEANUP_SECONDS, b.MAX_COMMANDS,
            b.OUTPUT_CAP, b.AGGREGATE_OUTPUT_CAP) == (1800, 60, 6, 8388608, 33554432)
    paths = {n: Path('$RUNNER_TEMP/pin-bitmap-lint-regression-v1-evidence/scratch') / n
             for n in ('source', 'target', 'cargo', 'home', 'nodebin')}
    plan = a.command_plan(paths, Path('$RUSTUP_HOME/toolchains') / a.TOOLCHAIN / 'bin',
                         Path('$RUNNER_TEMP/pin-bitmap-lint-regression-v1-evidence/scratch/rustfmt.toml'),
                         {'path': '$NODE_REALPATH'})
    assert json.loads(json.dumps(plan)) == b.json_data((ORIGINAL / 'command-plan.json').read_bytes())['commands']
    workflow = (HERE / 'workflow.yml').read_text()
    assert workflow == (BASE / 'workflow.yml').read_text().replace(OLD_SOURCE, NEW_SOURCE).replace(OLD_DRIVER, NEW_DRIVER)
    assert '/verification/swift-pin-bitmap-lint-host-evidence-correction/admit.py\n' in workflow
    assert basis['workflow']['proposed'] == row(HERE / 'workflow.yml')
    if installed_workflow:
        assert row(ROOT / a.WORKFLOW_PATH) == row(HERE / 'workflow.yml'), 'Installed workflow differs from proposal'
    if verify_seal:
        seal = b.json_data((HERE / 'seal.json').read_bytes())
        for name, expected in seal['files'].items():
            assert row(HERE / b.member(name)) == expected, 'Selected static packet drift: ' + name
        assert tree(seal['files']) == seal['treeSHA256']
        actual = {p.relative_to(HERE).as_posix() for p in HERE.rglob('*') if p.is_file()
                  and p.name not in RUNTIME_NAMES and p.name != 'seal.json'}
        assert actual == set(seal['files']), 'Unsealed static member present'
    assert not list(HERE.glob('pure-*')) and not list(HERE.rglob('__pycache__'))
    assert offline.ATTEMPTS == []
    return {'schema': 1, 'sourceOnly': True, 'candidateMembers': 136, 'overlays': 15,
            'candidateTreeSHA256': SOURCE_CLOSURE, 'sourceSealSHA256': SOURCE_SEAL,
            'workflowSHA256': row(HERE / 'workflow.yml')['sha256'],
            'installedWorkflowChecked': installed_workflow, 'staticSealChecked': verify_seal,
            'hostControls': 27, 'hostUnchangedBodies': 26, 'correctionControls': 16,
            'correctionUnchangedBodies': 14, 'exactAdmitBindingSubstitutions': 5,
            'typedSourceBindingsChecked': True, 'runtimeRuns': 0, 'liveApiAttempts': offline.ATTEMPTS,
            'validationScope': 'Guarded hashes, typed source bindings, exact minimal source/control/workflow diffs; no YAML/actionlint validation'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed-workflow', action='store_true')
    args = parser.parse_args()
    print(json.dumps(check(installed_workflow=args.installed_workflow), sort_keys=True))
