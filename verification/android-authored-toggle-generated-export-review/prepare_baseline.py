#!/usr/bin/env python3
"""Freeze independent expectations from immutable proposal/acceptance inputs only."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PROPOSAL = 'verification/android-public-appearance-routing-proposal/'
INTEGRATION = 'verification/android-authored-toggle-integration/'
INPUTS = [PROPOSAL + name for name in ['receipt.json', 'source-manifest.json',
                                      'source-excerpts.json', 'observations.json']]
INPUTS += [INTEGRATION + name for name in ['acceptance.json', 'integration.json',
                                         'host-1/fresh-artifacts.json']]
NAMES = ['Json', 'UiPacket', 'NativeRenderer', 'NativeBridge', 'MixerActivity',
         'NativeCoordinatorV2', 'AppearanceDescriptorV2', 'AppearanceGeometryV2',
         'AppearanceResolverV2', 'AppearanceNativePathsV2', 'InstalledAppearanceV2',
         'NativeEnvironmentV2', 'NativeAppearanceViewsV2', 'AuthoredToggleInputV2']


def digest(value):
    return hashlib.sha256(value).hexdigest()


def main():
    raw = {name: (ROOT / name).read_bytes() for name in INPUTS}
    data = {name: json.loads(value) for name, value in raw.items()}
    proposal = data[PROPOSAL + 'receipt.json']
    for name, expected in proposal['bindings'].items():
        assert digest(raw[PROPOSAL + name]) == expected
    accepted = data[INTEGRATION + 'acceptance.json']
    for name in ['integration.json', 'host-1/fresh-artifacts.json']:
        assert digest(raw[INTEGRATION + name]) == accepted['bindings'][INTEGRATION + name]
    manifest = data[PROPOSAL + 'source-manifest.json']['files']
    integration = data[INTEGRATION + 'integration.json']
    expected_java = {}
    for name in NAMES:
        path = 'native/android/app/src/dev/mixer/android/' + name + '.java'
        expected_java[path] = integration['productInputBindings'].get(path, manifest.get(path))
        assert expected_java[path], path
    activity = 'native/android/app/src/dev/mixer/android/MixerActivity.java'
    assert expected_java[activity] == manifest[activity]
    baseline = {
        'schema': 1, 'status': 'independent-expectations-frozen-awaiting-root-handoff',
        'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'sourceRevisionAtProposal': proposal['sourceRevision'],
        'proposalSelectedTreeSHA256': proposal['selectedSourceTreeSHA256'],
        'inputBindings': {name: digest(value) for name, value in raw.items()},
        'expectedJavaCount': 14,
        'expectedJavaSources': expected_java,
        'expectedRetainedAuthoredClassArtifacts': data[PROPOSAL + 'observations.json'][
            'retainedAcceptedAuthoredClassArtifacts'],
        'requiredProductDiff': {
            'cli/Sources/MixerBuild/AndroidProject.swift': 'One exact authored-source allowlist entry only.',
            'cli/Tests/MixerBuildTests/AndroidProjectTests.swift':
                'Exact 14-source expectation plus meaningful lock mutation/direct-driver rejection coverage.',
        },
        'requiredEvidence': [
            'Fresh actual CLI creation, with exact exported source bytes and adapter digest.',
            'Java17 compilation of only exported Java against SDK37 with lint/warnings as errors and empty sourcepath.',
            'Omitting the authored source fails for the missing type and cannot resolve it from the repository or prior classes.',
            'Official D8 minAPI28 converts the positive closure and contains authored/nested classes.',
            'Independent edit/remove/rename cases for coordinator and authored source reject both CLI and direct driver before output creation.',
            'Full argv, tools, logs, source/class/DEX hashes, failed attempts and owned scratch cleanup.',
        ],
        'preservedContracts': {
            'activitySourceSHA256': expected_java[activity],
            'publicV2Routing': False, 'signedPresentationOrHealth': False,
            'minimumCompileAPI': 28, 'privateV2RuntimeFloor': 36,
            'sharedAppearanceDefaultRequired': True,
            'resourceThemeLifecyclePlatformGapsStillPending': True,
        },
        'forbiddenDuringPreparation': [
            'Reading root mutable implementation files or collector before frozen handoff.',
            'Changing the original proposal packet.', 'Native runtime/device discovery/capture/UI automation.',
        ],
        'preparationScope': 'Source/evidence data reads only. No product/compiler execution.',
        'pythonVersion': sys.version,
        'invocation': ['python3', 'verification/android-authored-toggle-generated-export-review/prepare_baseline.py'],
        'collectorSHA256': digest(Path(__file__).read_bytes()),
    }
    output = HERE / 'baseline.json'
    output.write_text(json.dumps(baseline, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': baseline['status'], 'expectedJavaCount': 14,
                      'baselineSHA256': digest(output.read_bytes())}, sort_keys=True))


if __name__ == '__main__':
    main()
