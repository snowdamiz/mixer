"""Select two reviewed SDK changes; use a name that cannot shadow stdlib select."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import signal
import textwrap

signal.alarm(30)
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
PATHS = ['cli/Sources/MixerBuild/AndroidSDKCompatibility.swift',
    'cli/Sources/MixerBuild/Resources/android-build.py',
    'cli/Tests/MixerBuildTests/AndroidSDKCompatibilityTests.swift']
APPROVED = {'Sources/MixerUI/Authoring.swift': 'ef313b4f153199ce2b18d4cea75be7a61b82350dd4b17e7e3be84757898482c6',
    'Sources/MixerUI/Validation.swift': 'c8b5002b0809a27a56513073c36c8b0b530f8f10678b2728ee0b308f021b6773'}


def identity(path):
    assert path.is_file() and not path.is_symlink()
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def digest(files):
    return hashlib.sha256(''.join(name + '\0' + files[name]['sha256'] + '\n' for name in sorted(files)).encode()).hexdigest()


def save(name, data):
    with (OUT / name).open('x') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')


assert not (OUT / 'selection.json').exists()
observed = json.loads((ROOT / 'verification/github-delivery-binary-export-and-ui/swift-host-review/receipt.json').read_bytes())
assert observed['SDK_tests_passed'] == 132 and len(observed['new_axis_tests_passed']) == 9
before = {name: identity(ROOT / name) for name in PATHS}
swift = (ROOT / PATHS[0]).read_text()
start = swift.index('Data(#"""\n') + len('Data(#"""\n')
end = swift.index('\n        """#.utf8)', start)
raw = swift[start:end]
old = json.loads(raw)
assert old['id'] == 'mixer.android-source-pair.4'
assert raw == textwrap.indent(json.dumps(old, sort_keys=True, indent=2), '        ')
assert len(old['sdk_files']) == 22 and len(old['adapter_files']) == 23
assert digest(old['sdk_files']) == old['sdk_compatibility_sha256']
assert digest(old['adapter_files']) == old['adapter_compatibility_sha256']
new = json.loads(json.dumps(old))
changes = {}
for name, expected in old['sdk_files'].items():
    actual = identity(ROOT / 'sdk' / name)
    if name in APPROVED:
        assert actual['sha256'] == APPROVED[name] and actual != expected
        changes[name] = {'previous': expected, 'reviewed': actual}
        new['sdk_files'][name] = actual
    else:
        assert actual == expected, name
for name, expected in old['adapter_files'].items():
    actual = ROOT / 'native/android' / ('engine/' + name if name.startswith('Sources/') else name)
    assert identity(actual) == expected, name
assert set(changes) == set(APPROVED)
new['id'] = 'mixer.android-source-pair.5'
new['sdk_compatibility_sha256'] = digest(new['sdk_files'])
assert all(new[k] == old[k] for k in old if k not in {'id', 'sdk_files', 'sdk_compatibility_sha256'})
save('previous-profile.json', old)
save('selected-profile.json', new)
(ROOT / PATHS[0]).write_text(swift[:start] + textwrap.indent(json.dumps(new, sort_keys=True, indent=2), '        ') + swift[end:])
for name in PATHS[1:]:
    path = ROOT / name
    source = path.read_text()
    assert source.count('mixer.android-source-pair.4') == 1
    path.write_text(source.replace('mixer.android-source-pair.4', 'mixer.android-source-pair.5'))
save('selection.json', {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'baseline': observed['commit'], 'before': before, 'after': {name: identity(ROOT / name) for name in PATHS},
    'changes': changes, 'profile_id': new['id'], 'sdk_digest': new['sdk_compatibility_sha256'],
    'SDK_blob_changes': 2, 'other_SDK_blobs_unchanged': 20, 'adapter_blobs_unchanged': 23,
    'wire_default_descriptor_and_source_admission_code_unchanged': True,
    'immutable_previous_profiles_preserved': True,
    'held_Android_candidate_v5_retried_or_modified': False,
    'new_pair_is_distribution_identity_not_held_runtime_candidate': True,
    'SDK_scope': {'remote_passed': 132, 'new_multiline_passed': 9},
    'CLI_and_Python_corrected_execution': 'pending', 'native_or_release_or_GA_verified': False})
print(json.dumps({'profile': new['id'], 'SDK_digest': new['sdk_compatibility_sha256'], 'changed_SDK_rows': len(changes)}))
