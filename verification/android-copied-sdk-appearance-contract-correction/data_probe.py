#!/usr/bin/env python3
"""Data predicates only; not an implementation of or execution test for admission."""
import json
import pathlib

OUT = pathlib.Path(__file__).resolve().parent
INPUT = OUT / 'inputs/verification/android-copied-sdk-appearance-contract-review'
manifest = json.loads((OUT / 'source-manifest.json').read_text())
old_profile = json.loads((OUT / 'inputs/verification/android-copied-sdk-appearance-contract/proposed-profile-observation.json').read_text())
observed = json.loads((INPUT / 'probe-result.json').read_text())
baseline = json.loads((INPUT / 'host-probe/baseline-dump-package.stdout').read_text())
alternate = json.loads((INPUT / 'host-probe/alternate-manifest-dump-package.stdout').read_text())
target = lambda value: next(x for x in value['targets'] if x['name'] == 'MixerUI')
assert 'path' not in target(baseline)
assert target(alternate)['path'] == 'Sources/UnreviewedUI'
assert observed['alternate_manifest']['baseline']['profile_map_equal']
assert observed['alternate_manifest']['alternate-manifest']['profile_map_equal']
assert observed['sdk_projection_sha256'] == old_profile['sdk_compatibility_sha256']
assert observed['adapter_projection_sha256'] == old_profile['adapter_compatibility_sha256']
sdk = {p.removeprefix('sdk/'): manifest['files'][p] for p in manifest['sdk_projection']}
adapter = {p.removeprefix('native/android/').removeprefix('engine/'): manifest['files'][p] for p in manifest['adapter_projection']}
assert sdk == old_profile['sdk_files'] and adapter == old_profile['adapter_files']


def ascii_lower(text):
    return ''.join(chr(ord(c) + 32) if 'A' <= c <= 'Z' else c for c in text)


def root_name_allowed(name, kind):
    if ascii_lower(name).startswith('package'):
        return name == 'Package.swift' and kind == 'regular'
    return True  # Other source rules, not this manifest-namespace predicate.


vectors = []
cases = [('Package.swift', 'regular', True), ('Package@swift-6.4.swift', 'regular', False),
         ('Package@swift-6.3.swift', 'regular', False), ('Package@swift-999.swift', 'regular', False),
         ('package.swift', 'regular', False), ('PACKAGE.SWIFT', 'regular', False),
         ('pAcKaGe@swift-6.4.swift', 'regular', False), ('Package.swift.bak', 'regular', False),
         ('Package.resolved', 'regular', False), ('README.md', 'regular', True),
         ('Sources', 'directory', True)]
for name, kind, expected in cases:
    assert root_name_allowed(name, kind) is expected
    vectors.append({'name': name, 'kind': kind, 'manifest_namespace_allows': expected})
for name in ['Package.swift', 'Package@swift-6.4.swift']:
    for kind in ['symlink', 'fifo', 'directory', 'socket']:
        assert not root_name_allowed(name, kind)
        vectors.append({'name': name, 'kind': kind, 'manifest_namespace_allows': False})
# Type/length/bytes checks are separately required; this data-only predicate
# intentionally does not pretend to test filesystem access or any Swift function.
marker = '__MIXER_ANDROID_SOURCE_PROFILE_HEX__'
template = 'PROFILE_HEX = "' + marker + '"\n# build-only decoder; no executed source\n'
assert template.count(marker) == 1
payload = json.dumps({'profile': 'mixer.android-source-pair.1', 'sdk': old_profile['sdk_compatibility_sha256'],
                      'adapter': old_profile['adapter_compatibility_sha256']}, sort_keys=True).encode()
hex_data = payload.hex()
rendered = template.replace(marker, hex_data)
assert marker not in rendered and rendered.count(hex_data) == 1
assert json.loads(bytes.fromhex(hex_data))['sdk'] == old_profile['sdk_compatibility_sha256']
assert (template + template).count(marker) == 2
assert template.replace(marker, '').count(marker) == 0
try:
    bytes.fromhex(marker)
    raise AssertionError('Raw marker unexpectedly decoded')
except ValueError:
    pass
result = {'status': 'correction-data-predicates-pass', 'manifest_name_type_vectors': len(vectors),
          'vectors': vectors, 'retained_manifest_selection_observed': 'Sources/UnreviewedUI',
          'sdk_profile_files': len(sdk), 'adapter_profile_files': len(adapter),
          'sdk_digest': old_profile['sdk_compatibility_sha256'], 'adapter_digest': old_profile['adapter_compatibility_sha256'],
          'unchanged_maps_equal_to_accepted_git': True,
          'hex_data_checks': ['one-marker', 'missing-marker', 'duplicate-marker', 'one-rendered-literal', 'raw-marker-decode-fails', 'hex-json-roundtrip'],
          'scope': 'Synthetic name/type and hex-data predicates plus retained host-manifest result verification; no filesystem gate, product import, Python driver execution, Swift compiler or R2 ordering proof.'}
print(json.dumps(result, indent=2, sort_keys=True))
