#!/usr/bin/env python3
"""Seal only V4 host repairs, binding the exact reused V3 products."""
import datetime
import json
import pathlib
import run as r
b = r.BASE
assert not (b / 'packet-seal.json').exists(), 'Never overwrite sealed V4'
controls = r.read(b / 'host-controls.json')
r.require(controls['allRequiredGroupsPassed'] is True and all(r.sha(r.ROOT / name) == digest for name, digest in controls['sourceFiles'].items()), 'V4 controls incomplete or changed')
selection = b.parent / 'apple-toggle-keyboard-focus-v3-root-review/v4-repair-selection.json'
review = b.parent / 'apple-toggle-keyboard-focus-v3-independent-review/review-seal.json'
r.require(r.sha(selection) == 'b8ae22a67823022f397f5b0efca8d92bfcda75043f7415afb0cf102cd765a807' and r.sha(review) == '1bdd1261e466f241e63dfeec41c2d4d4baa0d6a4a1c93b39d0e34d7e3f6b0c39', 'Root selection/review identity changed')
reuse = r.read(b / 'immutable-reuse.json')
r.require(all(r.sha(r.ROOT / name) == digest for group in ['copiedFiles', 'previousBindings'] for name, digest in reuse[group].items()), 'Copied app/runner/oracle differs')
manifest = r.read(b / 'build-products-manifest.json')
r.require(r.h.tree(r.h.PRODUCTS) == manifest['products'], 'Exact V3 products differ')
r.h.product_archive_payload(manifest)
files = {str(p.relative_to(r.ROOT)): r.sha(p) for p in sorted(b.rglob('*')) if p.is_file() and not p.is_symlink() and p.relative_to(b).parts[0] not in ['build', 'runtime', 'runtime-direct', '__pycache__', '.scratch']}
external = [r.ROOT / 'docs/apple-toggle-keyboard-focus-v4-preparation.md', selection, review, r.V3 / 'packet-seal.json'] + [r.ROOT / name for name in controls['sourceFiles']]
for path in external: files[str(path.relative_to(r.ROOT))] = r.sha(path)
seal = {'schema': 'mixer.apple-toggle.keyboard-v4-diagnostic.1', 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'status': 'sealed-host-repairs-awaiting-root-review', 'files': files, 'excludedMutableSubtrees': ['verification/apple-toggle-keyboard-focus-v4/runtime/', 'verification/apple-toggle-keyboard-focus-v4/runtime-direct/'], 'rootSelectionSHA256': r.sha(selection), 'priorV3SealSHA256': r.sha(r.V3 / 'packet-seal.json'), 'candidateSourceClosureSHA256': 'f9ddf3e2615a80930d551351e1496f12ea476cac3e8d1bfd38d8cd101a1d2a46', 'candidateArchiveSHA256': 'b9a864d11182ac546d76110d7d4ea342821df98d1e32b3474e57cf07de04b393', 'testRunnerProductTreeSHA256': manifest['productTreeSHA256'], 'testRunnerArchiveSHA256': manifest['productArchiveSHA256'], 'focusedV4Controls': 22, 'adaptedIndependentV4Controls': 17, 'same44AssertionsV4FixtureOnly': 44, 'unchangedV3Controls': 44, 'unchangedV2Controls': 29, 'sealedV3Findings': '17 methods retain3finding methods with5failure records', 'expectedXCTestMethods': 1, 'applicationCasesUnrun': sorted(r.keyboard_oracle.CASES), 'recompiled': False, 'nativeExecuted': False, 'nativeInstancesQueried': False, 'nativeKeyboardQualification': False, 'carrierAccepted': False, 'gaAccepted': False}
(b / 'packet-seal.json').write_text(json.dumps(seal, indent=2, sort_keys=True) + '\n')
print(json.dumps({'sealSHA256': r.sha(b / 'packet-seal.json'), 'sealedFiles': len(files), 'status': 'DIAGNOSTIC_ONLY', 'recompiled': False, 'nativeExecuted': False}))
