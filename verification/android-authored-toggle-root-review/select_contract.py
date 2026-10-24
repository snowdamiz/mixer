"""Select the proposed repair; bind the one omitted copied seal explicitly."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PACKET = ROOT / 'verification/android-authored-toggle-input-contract'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
entry = lambda p: {'bytes': p.stat().st_size, 'sha256': sha(p)}
read = lambda p: json.loads(p.read_text())


def main():
    assert not (HERE / 'selection.json').exists(), 'preserve existing selection'
    seal = PACKET / 'packet-seal.json'
    assert sha(seal) == '53cb01159623403ced9e902a015cb28262d56e358c81e13a59e4b0a5cd8d478b'
    expected = read(seal)['files']
    actual = {str(p.relative_to(ROOT)) for p in PACKET.rglob('*') if p.is_file() and p != seal}
    actual.add('docs/android-authored-toggle-input-contract.md')
    omitted = 'verification/android-authored-toggle-input-contract/inputs/verification/android-pointer-native-diagnosis/packet-seal.json'
    assert len(expected) == 68 and actual - set(expected) == {omitted} and not set(expected) - actual
    for name, value in expected.items():
        assert not (ROOT / name).is_symlink() and entry(ROOT / name) == value
    inputs = read(PACKET / 'input-bindings.json')
    assert len(inputs) == 44
    for name, value in inputs.items():
        binding = {k: value[k] for k in ['bytes', 'sha256']}
        assert entry(ROOT / name) == binding == entry(PACKET / value['snapshot'])
    original_seal = 'verification/android-pointer-native-diagnosis/packet-seal.json'
    assert sha(ROOT / omitted) == inputs[original_seal]['sha256'] == '802e1939b44e43237471732c89bfd6132f4678622d5899ad759be35219e93e44'
    pre = read(HERE / 'model-preflight.json')
    for name, digest in pre['sourceBindings'].items():
        assert sha(ROOT / name) == digest
    assert 'Ran 16 tests' in (HERE / 'contract-model-replay.log').read_text()
    bindings = dict(expected)
    for p in [ROOT / omitted, seal, Path(__file__), HERE / 'model-preflight.json', HERE / 'contract-model-replay.log']:
        bindings[str(p.relative_to(ROOT))] = entry(p)
    result = {
        'schema': 1, 'status': 'root-selected-isolated-authored-toggle-input-implementation',
        'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'command': [sys.executable, '-B', str(Path(__file__))], 'pythonVersion': sys.version,
        'bindings': bindings, 'sourceInputsVerified': 44, 'hostProposedModelTests': 16,
        'selectedContract': 'docs/android-authored-toggle-input-contract.md',
        'packetMembershipErratum': {
            'initialRootCheck': 'AssertionError: exact owned membership expected 68 but observed 69',
            'initialCheckWrites': 0,
            'cause': 'Producer excludes all packet-seal.json basenames instead of only its exact top seal path',
            'omittedSnapshot': omitted,
            'preservedBytes': 'Already bound by original input-bindings.json; root independently verifies and explicitly binds here',
            'producerPacketMutated': False, 'rootBoundOwnedFilesExcludingTopSeal': 69,
        },
        'implementationOwnership': {
            'isolatedCandidateProductionPaths': [
                'native/android/app/src/dev/mixer/android/NativeAppearanceViewsV2.java',
                'native/android/app/src/dev/mixer/android/NativeRenderer.java',
                'native/android/app/src/dev/mixer/android/AuthoredToggleInputV2.java (optional pure production helper)',
            ],
            'constraint': 'Isolated candidate only. Optional helper contains actual pure geometry/state policy consumed by native adapter and host tests; no second admission authority or mirrored fixture model. No live edits before independent review/root integration.',
            'evidencePaths': ['docs/android-authored-toggle-input-implementation.md', 'verification/android-authored-toggle-input/**'],
            'unchangedNativeFixture': ['verification/android-pointer-oracle-repair/CoordinatorJoinActivity.java', 'verification/android-pointer-oracle-repair/CoordinatorJoinInstrumentation.java'],
            'buildAndRunner': 'New derived build/wrapper may bind changed product class/source/APK identities. Original fixtures, oracle, schedule and prior packets remain immutable. Root native dispatch follows source/runner review.',
        },
        'rootDecisions': [
            'Keep real Switch checked/accessibility/key activation with one authored touch owner; never feed platform carrier onTouchEvent.',
            'Use the same authored endpoints, full DOWN displacement, midpoint tie-to-initial, horizontal clamping and vertical corridor.',
            'Reuse Input.open/current binding fence; ordinary listener remains sole proposal path; cancellation/preview never emits JNI.',
            'Cancel on gate close/bind/rollback/lifecycle; never resurrect pressed state.',
            'Do not tune fixture coordinates or invisible drawable dimensions; no hidden-platform reflection.',
        ],
        'nativeRunAuthorized': False, 'productAccepted': False, 'gaAccepted': False,
    }
    (HERE / 'selection.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'bindings': len(bindings), 'inputs': 44, 'contractSelected': True, 'nativeRunAuthorized': False}))


if __name__ == '__main__':
    main()
