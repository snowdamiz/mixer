#!/usr/bin/env python3
"""Prepare the owned source-only integration; no runner or producer execution."""
import unittest.mock
import offline
offline.install()
import ast
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
ORIGINAL = HERE.parent / 'swift-pin-bitmap-lint-independent-admission'
CORRECTION = HERE.parent / 'swift-pin-bitmap-lint-host-evidence-correction'
REVIEW = HERE.parent / 'swift-pin-bitmap-lint-host-proposal-review'
SELECTED = 'verification/swift-pin-bitmap-lint-host-selection'


def row(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(name, value):
    (HERE / name).write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')


def diff(name, before, after):
    (HERE / name).write_text(''.join(difflib.unified_diff(
        before.splitlines(keepends=True), after.splitlines(keepends=True),
        fromfile='frozen/' + name.removesuffix('.diff'),
        tofile='selected/' + name.removesuffix('.diff'))))


bases = {}
for packet, expected in (
    (ORIGINAL, '2012b4f0aabe97ebc2c10a501ea0f1dcc06791b0b4dcc5db5bb80c371fb28238'),
    (CORRECTION, '2512656148042b14810b123aae2e85bbed5ee13b0c877e2cd212c7bc7d7c7f1d'),
    (REVIEW, '16b9a002222f2df7e2977d9cd90b441f066d7f982f529133e0abb1483e8383f9'),
):
    assert row(packet / 'seal.json')['sha256'] == expected
    seal = json.loads((packet / 'seal.json').read_text())
    for name, expected_row in seal['files'].items():
        assert row(packet / name) == expected_row
    bases[packet.name] = {'sealSHA256': expected, 'members': len(seal['files']),
                          'treeSHA256': seal['treeSHA256']}

for name in ('admit.py', 'bounded_commands.py', 'offline.py'):
    (HERE / name).write_bytes((CORRECTION / name).read_bytes())
(HERE / 'controls.py').write_bytes((CORRECTION / 'controls.py').read_bytes())

original_controls = (ORIGINAL / 'host_controls.py').read_text()
controls = original_controls.replace(
    "            'python3 -B verification/swift-pin-bitmap-lint-independent-admission/host_controls.py',",
    "            '|',", 1).replace(
    "            'python3 -B verification/swift-pin-bitmap-lint-independent-admission/admit.py run'])",
    "            'python3 -B " + SELECTED + "/admit.py run'])\n"
    "        self.assertEqual(re.findall(r'^          (python3 -B .+)$',text,re.M),[\n"
    "            'python3 -B " + SELECTED + "/host_controls.py',\n"
    "            'python3 -B " + SELECTED + "/controls.py'])", 1)
assert controls != original_controls
(HERE / 'host_controls.py').write_text(controls)
diff('host_controls.py.diff', original_controls, controls)

before_reuse = (ORIGINAL / 'reuse.json').read_text()
reuse = json.loads(before_reuse)
reuse['genericPreimage'] = {
    'path': 'verification/swift-pin-bitmap-lint-host-evidence-correction/admit.py',
    'sha256': row(CORRECTION / 'admit.py')['sha256'],
}
save('reuse.json', reuse)
diff('reuse.json.diff', before_reuse, (HERE / 'reuse.json').read_text())

before_workflow = (ORIGINAL / 'workflow.yml').read_text()
workflow = before_workflow.replace(
    '            /verification/swift-pin-bitmap-lint-independent-admission/\n',
    '            /verification/swift-pin-bitmap-lint-independent-admission/\n'
    '            /' + SELECTED + '/\n'
    '            /verification/swift-pin-bitmap-lint-host-evidence-correction/admit.py\n', 1).replace(
    '        run: python3 -B verification/swift-pin-bitmap-lint-independent-admission/host_controls.py\n',
    '        run: |\n'
    '          python3 -B ' + SELECTED + '/host_controls.py\n'
    '          python3 -B ' + SELECTED + '/controls.py\n', 1).replace(
    '        run: python3 -B verification/swift-pin-bitmap-lint-independent-admission/admit.py run\n',
    '        run: python3 -B ' + SELECTED + '/admit.py run\n', 1).replace(
    '            verification/swift-pin-bitmap-lint-independent-admission/host-controls-result.json\n',
    '            ' + SELECTED + '/host-controls-result.json\n'
    '            ' + SELECTED + '/controls-result.json\n', 1)
(HERE / 'workflow.yml').write_text(workflow)
diff('workflow.yml.diff', before_workflow, workflow)

def tests(text):
    tree = ast.parse(text)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Controls')
    return {n.name: ast.get_source_segment(text, n) for n in cls.body
            if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')}

before_tests, after_tests = tests(original_controls), tests(controls)
assert set(before_tests) == set(after_tests) and len(after_tests) == 27
changed = [n for n in before_tests if before_tests[n] != after_tests[n]]
assert changed == ['test_workflow_no_node_install_and_exact_scope']
assert len([n for n in before_tests if before_tests[n] == after_tests[n]]) == 26
assert (HERE / 'controls.py').read_bytes() == (CORRECTION / 'controls.py').read_bytes()
assert len(tests((HERE / 'controls.py').read_text())) == 16
assert offline.ATTEMPTS == []
save('source-basis.json', {
    'schema': 1, 'parentSuppliedRevision': '6d57e05e58e6d614e58a0a4dc0fad661264fb46f',
    'parentSuppliedGitTree': '8d7444955c4e6f2519b6e0823d52f131d180a1af', 'GitVerified': False,
    'frozenPackets': bases,
    'copiedCode': {n: {'source': str((CORRECTION / n).relative_to(ROOT)), **row(HERE / n)}
                   for n in ('admit.py', 'bounded_commands.py', 'offline.py', 'controls.py')},
    'originalHostControls': row(ORIGINAL / 'host_controls.py'),
    'hostControlChanges': changed, 'unchangedOriginalHostControlBodies': 26,
    'correctionControlBodiesByteIdentical': True,
    'reuseChanges': {'genericPreimage': reuse['genericPreimage'],
                     'allNineGenericFunctionsRetained': reuse['genericFunctions'],
                     'helperPreimageUnchanged': reuse['helperPreimage']},
    'workflow': {'source': 'verification/swift-pin-bitmap-lint-independent-admission/workflow.yml',
                 'before': row(ORIGINAL / 'workflow.yml'), 'proposed': row(HERE / 'workflow.yml'),
                 'canonicalTarget': '.github/workflows/swift-pin-bitmap-lint-regression-admission.yml',
                 'additionalSparsePaths': ['/' + SELECTED + '/',
                     '/verification/swift-pin-bitmap-lint-host-evidence-correction/admit.py'],
                 'changes': ['Add selected source folder and exact accepted formatter generic preimage to sparse checkout',
                             'Run both guarded control suites in existing two-minute control step',
                             'Run byte-identical corrected runner in existing six-child step',
                             'Upload both actual selected control JSON results; retain original runner-temp evidence paths'],
                 'validation': 'Structural source validation only; no YAML parser/actionlint available or executed'},
    'candidate': {'sealSHA256': '89505e8f873e5c225d711f8ae923bd8149db30a74603c49dddb523639cb11052',
                  'members': 136, 'overlays': 15,
                  'treeSHA256': '7f188bd7b0fe12244936bcbde3f1e4b2f9d9d3fedd43cacbf750d4ba55684748'},
})
print(json.dumps({'sourceOnly': True, 'originalHostTests': 27, 'unchangedBodies': 26,
                  'exactCorrectionTests': 16, 'liveApiAttempts': offline.ATTEMPTS}))
