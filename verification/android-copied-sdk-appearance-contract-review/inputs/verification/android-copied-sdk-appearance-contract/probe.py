#!/usr/bin/env python3
"""Offline contract vectors; this is not product admission or codec/ABI validation."""
import hashlib
import json
import pathlib

OUT = pathlib.Path(__file__).resolve().parent
SOURCES = OUT / 'source-inputs'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def identity(data):
    return {'bytes': len(data), 'sha256': sha(data)}


def projection_hash(files):
    h = hashlib.sha256()
    for path, value in sorted(files.items()):
        h.update((path + '\0' + value['sha256'] + '\n').encode('utf-8'))
    return h.hexdigest()


manifest = json.loads((OUT / 'source-manifest.json').read_text())
for path, expected in manifest['files'].items():
    assert identity((SOURCES / path).read_bytes()) == expected, path
frozen = SOURCES / 'verification/android-default-appearance-packaging'
seal = json.loads((frozen / 'seal.json').read_text())
verified_seal_members = []
for relative in ['handoff.json', 'run-2/product-before.json', 'run-2/final-descriptor.json',
                 'run-2/swift-final-codec-probe.stdout', 'run-2/java-final-codec-probe.stdout']:
    assert identity((frozen / relative).read_bytes()) == seal['files'][relative], relative
    verified_seal_members.append(relative)
handoff = json.loads((frozen / 'handoff.json').read_text())
selection_path = 'verification/android-default-appearance-packaging-root-review/implementation-selection.json'
assert sha((SOURCES / selection_path).read_bytes()) == handoff['selection_sha256']
assert handoff['implementation_accepted'] is False and handoff['GA_qualified'] is False
frozen_product = json.loads((frozen / 'run-2/product-before.json').read_text())['files']
sdk = {p.removeprefix('sdk/'): manifest['files'][p] for p in manifest['sdk_projection']}
adapter = {p.removeprefix('native/android/').removeprefix('engine/'): manifest['files'][p]
           for p in manifest['adapter_projection']}
source_drift = [p for p in manifest['sdk_projection'] + manifest['adapter_projection']
                if manifest['files'][p] != frozen_product[p]]
assert not source_drift, source_drift
descriptor = (frozen / 'run-2/final-descriptor.json').read_bytes()
assert identity(descriptor) == handoff['observations']['descriptor']
default = json.loads(descriptor)
assert default['format'] == 'mixer.native-appearance.2'
assert default['mode'] == 'shared' and default['resources'] == []
assert default['theme']['typography']['font'] == {'kind': 'systemSans'}
# This checks retained data shape only. Swift/Java codec outcomes are historical
# sealed outputs, and are not re-executed by this probe.
expected = projection_hash(sdk)
vectors = []


def case(name, files, accepted, **extra):
    observed = projection_hash(files) == expected and set(files) == set(sdk)
    assert observed is accepted, name
    vectors.append({'name': name, 'proposed_profile_accepts': observed, **extra})


case('same-reviewed-source-map', dict(sdk), True)
for name, path in [('changed-default-producer', 'Sources/MixerUI/AppearanceDefaultV2.swift'),
                   ('changed-api-with-same-descriptor-bytes', 'Sources/MixerUI/Protocol.swift'),
                   ('changed-packet-encoder-with-same-descriptor-bytes', 'Sources/MixerUI/NativePacketV1.swift'),
                   ('changed-manifest-with-same-descriptor-bytes', 'Package.swift')]:
    changed = dict(sdk)
    changed[path] = identity(b'synthetic contract drift; not compiled or executed')
    case(name, changed, False, descriptor_sha256_unchanged=sha(descriptor))
for name in ['missing-required-source', 'renamed-required-source']:
    changed = dict(sdk)
    value = changed.pop('Sources/MixerUI/Protocol.swift')
    if name.startswith('renamed'):
        changed['Sources/MixerUI/Renamed.swift'] = value
    case(name, changed, False)
for name, path in [('extra-swift-source', 'Sources/MixerUI/Injected.swift'),
                   ('extra-unknown-extension', 'Sources/MixerUI/Injected.txt'),
                   ('excluded-name-inside-required-source-directory', 'Sources/MixerUI/.env')]:
    changed = dict(sdk)
    changed[path] = identity(b'extra')
    case(name, changed, False)
# The proposed SDK projection deliberately does not claim other targets/logs/tests.
case('unrelated-sdk-target-test-or-log-change-outside-projection', dict(sdk), True,
     limitation='Full sdkDigest still changes/locks such copied files; native/API claim remains restricted to the pinned manifest and Core/UI.')
assert len(vectors) == 11
profile = {'schema': 1, 'id': 'mixer.android-source-pair.1-proposed',
           'sdk_compatibility_sha256': expected,
           'adapter_compatibility_sha256': projection_hash(adapter),
           'default_descriptor': identity(descriptor),
           'sdk_files': sdk, 'adapter_files': adapter,
           'wire': {'document_schema': 1, 'native_packet_schema': 1,
                    'appearance_format': 'mixer.native-appearance.2', 'appearance_recipe': 'measuredShared2',
                    'android_profile_id': 'mixer-android-native-v1-development',
                    'staged_C_ABI': 'private-unversioned-v2-not-public-stable'}}
(OUT / 'proposed-profile-observation.json').write_text(json.dumps(profile, indent=2, sort_keys=True) + '\n')
report = {'status': 'offline-data-contract-vectors-pass',
          'vectors': vectors, 'vector_count': len(vectors),
          'sdk_projection_files': len(sdk), 'adapter_projection_files': len(adapter),
          'sdk_compatibility_sha256': expected, 'adapter_compatibility_sha256': projection_hash(adapter),
          'descriptor': identity(descriptor), 'selected_frozen_seal_members_verified': verified_seal_members,
          'selected_source_drift_from_frozen_packet': source_drift,
          'authority': 'Illustrates proposed map identity only; no product gate, Swift/Java codec execution, ABI proof or package authenticity.',
          'native_runtime_or_capture_started': False}
print(json.dumps(report, indent=2, sort_keys=True))
