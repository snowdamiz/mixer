#!/usr/bin/env python3
"""Seal this separately selected setup diagnostic without altering prior packets."""
import datetime
import json
import pathlib
import run as r
b = r.BASE
assert not (b / 'packet-seal.json').exists(), 'Never overwrite a sealed preparation'
controls = r.read(b / 'host-controls.json')
r.require(controls['exitCode'] == 0 and controls['testsRun'] == controls['expectedTestsRun'] == 44, 'Controls incomplete')
r.require(all(r.sha(r.ROOT / name) == digest for name, digest in controls['sourceFiles'].items()), 'Control sources changed')
selection = r.ROOT / 'verification/apple-toggle-keyboard-focus-v3-root-review/selection.json'
r.require(r.sha(selection) == '703d2c5db1e79b8eaf4b17fba95bd660de598cf575ed861b08b6c70115bdeb28', 'Root diagnostic selection changed')
manifest = r.read(b / 'build-products-manifest.json')
r.require(r.h.tree(r.h.PRODUCTS) == manifest['products'], 'Cross-built Products changed')
r.h.product_archive_payload(manifest)
files = {str(p.relative_to(r.ROOT)): r.sha(p) for p in sorted(b.rglob('*')) if p.is_file() and not p.is_symlink() and p.relative_to(b).parts[0] not in ['build', 'runtime', 'runtime-direct', '__pycache__']}
external = [r.ROOT / 'docs/apple-toggle-keyboard-focus-v3-preparation.md', selection, r.V2 / 'packet-seal.json', r.PREVIOUS / 'packet-seal.json']
external += [r.ROOT / name for name in r.read(b / 'diagnosis.json')['inputs']]
for p in external:
    files[str(p.relative_to(r.ROOT))] = r.sha(p)
seal = {'schema': 'mixer.apple-toggle.keyboard-v3-diagnostic.1', 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'status': 'sealed-host-and-crossbuild-setup-diagnostic-awaiting-root-review', 'sourceRevisionContext': r.h.SOURCE_REVISION_CONTEXT,
        'candidateSourceClosureSHA256': 'f9ddf3e2615a80930d551351e1496f12ea476cac3e8d1bfd38d8cd101a1d2a46', 'candidateArchiveSHA256': 'b9a864d11182ac546d76110d7d4ea342821df98d1e32b3474e57cf07de04b393',
        'testRunnerProductTreeSHA256': manifest['productTreeSHA256'], 'testRunnerArchiveSHA256': manifest['productArchiveSHA256'], 'files': files,
        'excludedMutableSubtrees': ['verification/apple-toggle-keyboard-focus-v3-preparation/runtime/', 'verification/apple-toggle-keyboard-focus-v3-preparation/runtime-direct/'],
        'hostTestMethods': 44, 'unchangedV2RegressionMethods': 29, 'expectedXCTestMethods': 1, 'applicationCasesUnrun': sorted(r.keyboard_oracle.CASES),
        'bounds': {'requestBytes': 8192, 'decodedChunkBytes': 3072, 'imageBytes': 2000000, 'axTreeBytes': 200000, 'decodedTotalBytes': 7000000, 'requests': 2500, 'uploads': 32, 'events': 100, 'polls': 40, 'diagnosticSeconds': 29, 'requestSeconds': 2, 'sessionSeconds': 600, 'switchObservationSeconds': 3},
        'deadlinePolicy': 'The single conditional tap return or initial-enabled raw observation anchors the3s window; capture/telemetry cannot reset it, and late one cannot satisfy the observation. Uploads have no retry and share the29s diagnostic/session-clamped deadline.',
        'completionPolicy': 'Inherited qualification assertion and all independent cleanup remain unchanged. Its exit0/strict-native assertion failure is identified as expected diagnostic boundary; Settings/XCTest failures stay failures.',
        'statusPolicy': 'Every outcome DIAGNOSTIC_ONLY; six app cases unrun even if setup succeeds. No hardware-keyboard configuration or private preferences.',
        'appOrCarrierChanged': False, 'strictV2OracleChanged': False, 'nativeExecuted': False, 'nativeInstancesQueried': False, 'physicalDevicesQueried': False, 'nativeKeyboardQualification': False, 'carrierAccepted': False, 'gaAccepted': False}
(b / 'packet-seal.json').write_text(json.dumps(seal, indent=2, sort_keys=True) + '\n')
print(json.dumps({'sealSHA256': r.sha(b / 'packet-seal.json'), 'sealedFiles': len(files), 'status': 'DIAGNOSTIC_ONLY', 'nativeExecuted': False}))
