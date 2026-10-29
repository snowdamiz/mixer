#!/usr/bin/env python3
"""One guarded Python bootstrap: source rebind, copied controls, evidence and seal."""
import unittest.mock
import offline
offline.install()
import argparse
import ast
import datetime
import difflib
import hashlib
import importlib
import io
import json
from pathlib import Path
import re
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
BASE = HERE.parent / 'swift-pin-bitmap-lint-host-selection'
REVIEW = HERE.parent / 'swift-pin-bitmap-lint-actual-review'
SOURCE = HERE.parent / 'swift-pin-bitmap-match-binding-correction'
OLD_SOURCE = 'verification/swift-pin-bitmap-lint-correction'
NEW_SOURCE = 'verification/swift-pin-bitmap-match-binding-correction'
OLD_DRIVER = 'verification/swift-pin-bitmap-lint-host-selection'
NEW_DRIVER = 'verification/swift-pin-bitmap-match-host-admission'


def row(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')


def tree(rows):
    return hashlib.sha256(''.join(n + '\0' + rows[n]['sha256'] + '\n'
                                  for n in sorted(rows)).encode()).hexdigest()


def packet(path, sha):
    assert row(path / 'seal.json')['sha256'] == sha
    seal = json.loads((path / 'seal.json').read_text())
    for name, expected in seal['files'].items():
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        assert row(path / name) == expected
    assert tree(seal['files']) == seal['treeSHA256']
    return seal


def replace_exact(text, before, after, count):
    assert text.count(before) == count, (before, text.count(before), count)
    return text.replace(before, after, count)


def tests(text):
    cls = next(n for n in ast.parse(text).body if isinstance(n, ast.ClassDef) and n.name == 'Controls')
    return {n.name: ast.get_source_segment(text, n) for n in cls.body
            if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')}


def suite(name, count, archive):
    module = importlib.import_module(name)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(module.Controls))
    text = stream.getvalue()
    (HERE / 'outputs' / (archive + '-test-output.txt')).write_text(text)
    sys.stderr.write(text)
    record = {'schema': 1, 'tests': result.testsRun, 'failures': len(result.failures),
              'errors': len(result.errors), 'skips': len(result.skipped), 'pythonVersion': sys.version,
              'guardBeforeSubjectImports': True, 'liveApiAttempts': offline.ATTEMPTS,
              'realNestedProcessSessionGroupSignalTimerWaitSocketCalls': 0,
              'RustNodeSwiftElixirCompilerProductRuntimeRuns': 0,
              'scope': 'Guarded source and mocked behavior; no actual compiler/Node/custody evidence',
              'scratchRemaining': [p.name for p in HERE.glob('pure-*')]}
    save(HERE / 'outputs' / (archive + '.json'), record)
    assert result.testsRun == count and result.wasSuccessful(), 'Guarded suite failed'
    assert not result.skipped and not offline.ATTEMPTS and not record['scratchRemaining']
    return record


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-seal', required=True)
parser.add_argument('--source-members', required=True, type=int)
parser.add_argument('--source-closure', required=True)
args = parser.parse_args()
assert not (HERE / 'seal.json').exists(), 'Refuse replacing an immutable selected packet'
assert re.fullmatch('[0-9a-f]{64}', args.source_seal)
assert re.fullmatch('[0-9a-f]{64}', args.source_closure)
assert 15 < args.source_members < 100
bases = {}
for path, sha in ((BASE, 'd8368ae3e4287e56b8dff3f0533c50b415a61cc30e20590875d4612c16afe239'),
                  (REVIEW, 'ba20b76ea587bf52620908fd1d56a53bbd22d4ab74908abbb71308e4de9ebf47'),
                  (SOURCE, args.source_seal)):
    seal = packet(path, sha)
    bases[path.name] = {'sealSHA256': sha, 'members': len(seal['files']), 'treeSHA256': seal['treeSHA256']}
assert bases[SOURCE.name]['members'] == args.source_members
assert row(BASE / 'admit.py')['sha256'] == 'd477eeabdfc08f629a3782e306958ea4c5db6102a680d30296e0211335693302'
assert row(BASE / 'bounded_commands.py')['sha256'] == '93cc3c4ae578a3f5bf01c09cd143859c48ee3e7b473f9c8f34ead1f60724bee9'

replacements = [
    {'before': "PACKET = ROOT / '" + OLD_SOURCE + "'", 'after': "PACKET = ROOT / '" + NEW_SOURCE + "'", 'count': 1},
    {'before': "SEAL_SHA = '89505e8f873e5c225d711f8ae923bd8149db30a74603c49dddb523639cb11052'", 'after': "SEAL_SHA = '" + args.source_seal + "'", 'count': 1},
    {'before': "CANDIDATE = '7f188bd7b0fe12244936bcbde3f1e4b2f9d9d3fedd43cacbf750d4ba55684748'", 'after': "CANDIDATE = '" + args.source_closure + "'", 'count': 1},
    {'before': "need(len(sealed['files']) == 31, 'Exact 31 sealed input members')", 'after': "need(len(sealed['files']) == " + str(args.source_members) + ", 'Exact " + str(args.source_members) + " sealed input members')", 'count': 1},
    {'before': "'" + OLD_SOURCE + "/candidate/vm/'", 'after': "'" + NEW_SOURCE + "/candidate/vm/'", 'count': 1},
]
text = (BASE / 'admit.py').read_text()
for binding in replacements:
    text = replace_exact(text, **binding)
(HERE / 'admit.py').write_text(text)
for name in ('bounded_commands.py', 'offline.py', 'reuse.json'):
    (HERE / name).write_bytes((BASE / name).read_bytes())

host = (BASE / 'host_controls.py').read_text()
host = host.replace(OLD_SOURCE, NEW_SOURCE).replace(OLD_DRIVER, NEW_DRIVER)
(HERE / 'host_controls.py').write_text(host)

control = (BASE / 'controls.py').read_text()
control = replace_exact(control,
    "        new = ast.parse((HERE / 'admit.py').read_text())",
    "        rebound = (HERE / 'admit.py').read_text()\n"
    "        bindings = json.loads((HERE / 'source-basis.json').read_text())['admitReplacements']\n"
    "        for binding in bindings:\n"
    "            self.assertEqual(rebound.count(binding['after']), binding['count'])\n"
    "            rebound = rebound.replace(binding['after'], binding['before'], binding['count'])\n"
    "        self.assertEqual(rebound, (HERE.parent / 'swift-pin-bitmap-lint-host-evidence-correction' / 'admit.py').read_text())\n"
    "        new = ast.parse(rebound)", 1)
control = replace_exact(control,
    "(136, 15, '7f188bd7b0fe12244936bcbde3f1e4b2f9d9d3fedd43cacbf750d4ba55684748')",
    "(136, 15, '" + args.source_closure + "')", 1)
(HERE / 'controls.py').write_text(control)
workflow = (BASE / 'workflow.yml').read_text().replace(OLD_SOURCE, NEW_SOURCE).replace(OLD_DRIVER, NEW_DRIVER)
(HERE / 'workflow.yml').write_text(workflow)
for name in ('admit.py', 'host_controls.py', 'controls.py', 'workflow.yml'):
    before, after = (BASE / name).read_text(), (HERE / name).read_text()
    (HERE / (name + '.diff')).write_text(''.join(difflib.unified_diff(
        before.splitlines(keepends=True), after.splitlines(keepends=True),
        fromfile='accepted/' + name, tofile='rebound/' + name)))

basis = {'schema': 1, 'parentSuppliedRevision': '88c32d7fe9a5596d269ad29eb63c380dc5e820b4',
         'parentSuppliedGitTree': '6bca344641b9b4c9e928a460b801f8c93d2a90ad', 'GitVerified': False,
         'frozenPackets': bases, 'admitReplacements': replacements,
         'copiedByteIdentical': {n: row(HERE / n) for n in ('bounded_commands.py', 'offline.py', 'reuse.json')},
         'candidate': {'path': NEW_SOURCE, 'members': 136, 'overlays': 15,
                       'sealedMembers': args.source_members, 'sealSHA256': args.source_seal,
                       'treeSHA256': args.source_closure,
                       'baselineTreeSHA256': 'af0db424af7b08f013d2c6a8894f4d156f76bc5f493620c6f2c0b85d3bf4c48b',
                       'materializationPrefix': NEW_SOURCE + '/candidate/vm/'},
         'hostControlChanges': ['test_workflow_no_node_install_and_exact_scope'],
         'correctionControlChanges': ['test_only_two_functions_and_one_small_roster_helper_change',
                                      'test_real_source_admission_and_exact_six_vectors_remain'],
         'controlsPreserved': {'hostUnchangedBodies': 26, 'correctionUnchangedBodies': 14,
                              'noAssertionsRemoved': True},
         'workflow': {'canonicalTarget': '.github/workflows/swift-pin-bitmap-lint-regression-admission.yml',
                      'before': row(BASE / 'workflow.yml'), 'proposed': row(HERE / 'workflow.yml'),
                      'validation': 'Structural source checks only; no YAML parser/actionlint available or executed'},
         'previousSpentAttempt': {'runID': 40822264739, 'attempt': 1, 'newAttemptSelected': False},
         'actualFormattedPreimage': '1c24099923de0e10835957cb7a8cdc744750014aae360dac5ffe8dccb3f9b60a'}
save(HERE / 'source-basis.json', basis)
import verify
source_check = verify.check(verify_seal=False)
host_result = suite('host_controls', 27, 'local-host-controls')
correction_result = suite('controls', 16, 'local-correction-controls')
save(HERE / 'outputs' / 'local-source-check.json', source_check)
assert offline.ATTEMPTS == []
receipt = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'decision': 'Source-only rebound host packet for root review; no new hosted attempt authorized',
           'command': 'python3 -B ' + NEW_DRIVER + '/prepare.py --source-seal ' + args.source_seal
                      + ' --source-members ' + str(args.source_members) + ' --source-closure ' + args.source_closure,
           'commandExit': 0, 'pythonVersion': sys.version,
           'parentSuppliedRevision': basis['parentSuppliedRevision'],
           'parentSuppliedGitTree': basis['parentSuppliedGitTree'], 'GitVerified': False,
           'candidate': basis['candidate'], 'workflow': basis['workflow'],
           'controls': {'host': 27, 'correction': 16, 'passed': 43, 'failures': 0, 'errors': 0,
                        'skips': 0, 'suiteRuns': 2, 'failedSuiteRuns': 0, 'guardBeforeSubjectImports': True,
                        'hostUnchangedBodies': 26, 'correctionUnchangedBodies': 14,
                        'scope': 'Source and mock assertions only; no live compiler/Node/custody evidence'},
           'outputs': {p.relative_to(HERE).as_posix(): row(p) for p in sorted((HERE / 'outputs').glob('*'))},
           'sourceCheck': source_check, 'liveApiAttempts': [],
           'realNestedProcessSessionGroupSignalTimerWaitSocketCalls': 0,
           'RustNodeSwiftElixirCompilerProductRuntimeRuns': 0, 'nativeUICapturePhoneRuns': 0,
           'GitGhDispatchActions': 0, 'canonicalFilesEdited': False, 'frozenPacketsWritten': False,
           'cleanup': {'pureScratchRemaining': [], 'runtimeInstancesStarted': 0,
                       'heldProcessesProbed': False, 'onlyOwnedFolderWritten': True, 'otherProjectsTouched': False},
           'FieldLog': {'runID': 40802230894, 'pgid': 2424, 'pid': 2621, 'probedSignalledRetried': False},
           'newAttemptAuthorization': False, 'workflowInstalled': False, 'GAQualified': False,
           'pending': ['root source review and attempt selection', 'remote formatter/Clippy/full Debug/Release',
                       'native/physical/published-package FieldLog/store/customer/GA'],
           'limitations': ['No compiler, product, Node oracle or live custody execution',
                           'Structural workflow source check only; no YAML parser/actionlint',
                           'Existing installer custody, descendant, Node pipe/reap, shared-library and evidence-I/O limits unchanged']}
save(HERE / 'receipt.json', receipt)
files = {p.relative_to(HERE).as_posix(): row(p) for p in sorted(HERE.rglob('*'))
         if p.is_file() and p.name not in verify.RUNTIME_NAMES and p.name != 'seal.json'}
save(HERE / 'seal.json', {'schema': 1, 'scope': 'Source-only corrected bitmap host rebind; no attempt selected',
                         'runtimeResultNamesExcluded': sorted(verify.RUNTIME_NAMES),
                         'files': files, 'treeSHA256': tree(files)})
verify.check()
print(json.dumps({'sourceOnly': True, 'controlsPassed': 43, 'members': len(files),
                  'treeSHA256': tree(files), 'sealSHA256': row(HERE / 'seal.json')['sha256'],
                  'workflowSHA256': row(HERE / 'workflow.yml')['sha256'],
                  'candidateTreeSHA256': args.source_closure, 'liveApiAttempts': offline.ATTEMPTS}, sort_keys=True))
