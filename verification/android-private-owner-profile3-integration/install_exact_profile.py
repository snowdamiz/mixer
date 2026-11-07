"""Apply only the root-selected immutable profile, never derive a permissive lock."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
def bind(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

selection = ROOT / 'verification/android-private-owner-effect-integration-root-review/candidate-3-profile-selection.json'
assert bind(selection)['sha256'] == 'bc6ffacdd63674ba1c6d3a5bbf8c86f965e191d22113056157c116255e73b542'
profile_path = ROOT / 'verification/android-private-owner-integration-implementation/candidate-3/profile-proposal.json'
assert bind(profile_path)['sha256'] == '1133abb582662b8187b77f2fa4a9132db3f824502d4ea8d19557c2b340a006aa'
profile = json.loads(profile_path.read_bytes())
source = ROOT / 'cli/Sources/MixerBuild/AndroidSDKCompatibility.swift'
driver = ROOT / 'cli/Sources/MixerBuild/Resources/android-build.py'
before = {p.relative_to(ROOT).as_posix(): bind(p) for p in (source, driver)}
original = source.read_text()
prefix, tail = original.split('Data(#"""\n', 1)
old_json, suffix = tail.split('\n        """#.utf8)', 1)
old = json.loads(old_json)
assert old['id'] == 'mixer.android-source-pair.2'
for key in ('sdk_files', 'sdk_compatibility_sha256', 'default_descriptor', 'wire'):
    assert old[key] == profile[key]
assert len(profile['adapter_files']) == len(profile['sdk_files']) == 22
assert profile['adapter_compatibility_sha256'] == '72d824927975b54cf0d4dba17c793b07743484f648feab1656a0f42c6accebb4'
assert profile['id'] == 'mixer.android-source-pair.3'
(HERE / 'before').mkdir()
(HERE / 'before/AndroidSDKCompatibility.swift').write_text(original)
(HERE / 'before/android-build.py').write_bytes(driver.read_bytes())
(HERE / 'before/profile2.json').write_text(json.dumps(old, indent=2) + '\n')
rendered = '\n'.join('        ' + line for line in json.dumps(profile, indent=2).splitlines())
changed = prefix + 'Data(#"""\n' + rendered + '\n        """#.utf8)' + suffix
assert 'Selected frozen 22 + 20 map' in changed
source.write_text(changed.replace('Selected frozen 22 + 20 map', 'Selected frozen 22 + 22 map'))
text = driver.read_text()
assert text.count("mixer.android-source-pair.2") == 1
assert text.count("('adapter', 20)") == 1
driver.write_text(text.replace('mixer.android-source-pair.2', 'mixer.android-source-pair.3').replace("('adapter', 20)", "('adapter', 22)"))
receipt = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'command': sys.argv, 'python': sys.version, 'script': bind(Path(__file__)),
    'selection': bind(selection), 'profile': bind(profile_path), 'before': before,
    'after': {p.relative_to(ROOT).as_posix(): bind(p) for p in (source, driver)},
    'status': 'exact-profile-installed-validation-pending',
    'source_map_generated_from_live_tree': False, 'profile2_auto_migration': False,
    'native_source_changed': False, 'native_runtime_or_capture_started': False, 'GA_qualified': False}
(HERE / 'installation.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'profile': profile['id'], 'adapter_members': 22, 'sdk_members': 22, 'validation': 'pending'}))
