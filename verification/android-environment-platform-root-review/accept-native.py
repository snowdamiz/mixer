#!/usr/bin/env python3
"""Accept the exact bounded native environment bytes in private host/source scope."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent

def demand(ok, message):
    if not ok:
        raise ValueError(message)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

packets = []
for name, expected, count, size in [
    ('android-environment-platform-implementation', '161c47daa9c07cd01252327f31b814ed3a3f708587f2ed84adaee81b902cfacf', 1258, 17113061),
    ('android-environment-platform-independent', '0912ccdf0ad7b09c5bef249cc4db4cd4d952dd08863de3ffe06435644ce60a9b', 197, 2562333),
]:
    path = ROOT / 'verification' / name / 'manifest.json'
    demand(digest(path) == expected, 'Manifest identity')
    files = json.loads(path.read_text())['files']
    demand(len(files) == count and sum(r['bytes'] for r in files.values()) == size, 'Packet totals')
    for name, row in files.items():
        member = ROOT / name
        demand(member.stat().st_size == row['bytes'] and digest(member) == row['sha256'], name)
    packets.append({'manifest': str(path.relative_to(ROOT)), 'sha256': expected, 'members_verified': count, 'bytes': size})
review_path = ROOT / 'verification/android-environment-platform-independent/acceptance.json'
review = json.loads(review_path.read_text())
demand(not review['blocking_findings'] and review['independent_host_cases'] == 76 and review['independent_host_assertions'] == 661, 'Review evidence')
demand(digest(HERE / 'selection.json') == review['selected_contract_sha256'], 'Selected contract')
source_files = {}
for name in ['NativeEnvironmentV2.java', 'NativeEnvironmentPlatformV2.java']:
    path = ROOT / 'native/android/app/src/dev/mixer/android' / name
    source_files[str(path.relative_to(ROOT))] = {'bytes': path.stat().st_size, 'sha256': digest(path)}
receipt = {
    'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'argv': sys.argv, 'python': sys.version, 'selector_sha256': digest(Path(__file__)),
    'packets': packets, 'root_contract_sha256': digest(HERE / 'selection.json'),
    'independent_acceptance_sha256': digest(review_path), 'source_files': source_files,
    'decision': 'Accept exact bounded A native implementation for private development host/source scope',
    'native_implementation_host_source_accepted': True,
    'independent_host_cases': 76, 'independent_host_assertions': 661,
    'official_Java17_SDK37_D8min28': 'passed cross-compilation only',
    'nonadapter_environment_classes_checked': 16, 'official_members_checked': 15,
    'protected_files_checked': 69, 'barrier_anchors_checked': 189,
    'all_source_profile4_CLI_acceptance_separate': True,
    'known_value_and_failure_diagnostic_separate': True,
    'ordinary_failure_original_identity_preserved': True,
    'fresh_reads_and_exact_retained_listener_targets_distinguished': True,
    'both_API36_guards_preserved': True, 'new_rendering_contexts_admitted': False,
    'public_V2_selected': False, 'native_runtime_qualified': False, 'GA_qualified': False,
    'no_native_UI_capture_or_process_inventory': True,
    'owned_host_children_reaped_and_scratch_removed': True,
    'limits': review['pending'],
}
target = HERE / 'native-acceptance.json'
demand(not target.exists(), 'Immutable acceptance already exists')
target.write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'path': str(target.relative_to(ROOT)), 'sha256': digest(target), 'members_verified': 1455, 'scope': receipt['decision']}))
