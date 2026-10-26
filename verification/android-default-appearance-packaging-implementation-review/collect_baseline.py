#!/usr/bin/env python3
"""Freeze accepted Git source and independent assertions before implementation access."""
import datetime
import hashlib
import json
import pathlib
import platform
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = pathlib.Path(__file__).resolve().parent
REVISION = '99d6384306ea17643b70c472f93b57418c674f86'
SELECTION_PATH = 'verification/android-default-appearance-packaging-root-review/implementation-selection.json'
SELECTION_SHA256 = '30171f00f98ed7e27c8f9654f0c997a7c9672e282697a7a4c8fa7bfca1d98582'
SOURCES = [
    'cli/Package.swift', 'cli/Sources/MixerCLI/main.swift',
    'cli/Sources/MixerBuild/AndroidProject.swift', 'cli/Sources/MixerBuild/ProjectGenerator.swift',
    'cli/Sources/MixerBuild/ProcessRunner.swift', 'cli/Sources/MixerBuild/Configuration.swift',
    'cli/Sources/MixerBuild/Resources/android-build.py',
    'cli/Tests/MixerBuildTests/AndroidProjectTests.swift', 'cli/build-tests/test_android_staging.py',
    'sdk/Package.swift', 'sdk/Sources/MixerUI/AppearanceDefaultV2.swift',
    'sdk/Sources/MixerUI/AppearanceDescriptorV2.swift', 'sdk/Sources/MixerUI/AppearanceValuesV2.swift',
    'native/android/app/src/dev/mixer/android/InstalledAppearanceV2.java',
    'native/android/app/src/dev/mixer/android/MixerActivity.java',
    'native/android/app/src/dev/mixer/android/NativeEnvironmentV2.java', 'mixer-product-plan.md',
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write(name, value):
    (BASE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def main():
    commands = []
    def command(argv):
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=15, check=False)
        commands.append({'argv': argv, 'exit_code': result.returncode,
                         'stdout_bytes': len(result.stdout), 'stdout_sha256': digest(result.stdout),
                         'stderr': result.stderr.decode()})
        if result.returncode:
            raise RuntimeError('Accepted-source command failed: ' + repr(argv))
        return result.stdout
    selection = (ROOT / SELECTION_PATH).read_bytes()
    assert digest(selection) == SELECTION_SHA256
    (BASE / 'implementation-selection.json').write_bytes(selection)
    git_version = command(['git', '--version']).decode().strip()
    files = []
    for name in SOURCES:
        # Deliberately do not read any working-tree product input.
        data = command(['git', 'show', REVISION + ':' + name])
        target = BASE / 'accepted-sources' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        files.append({'path': name, 'bytes': len(data), 'sha256': digest(data)})
    files.sort(key=lambda row: row['path'])
    source_digest = digest(''.join(row['path'] + '\0' + row['sha256'] + '\n' for row in files).encode())
    write('accepted-source-manifest.json', {
        'revision': REVISION, 'files': files, 'selected_source_sha256': source_digest,
        'digest_definition': 'SHA256 of sorted UTF8 path + NUL + lowercase file SHA256 + LF rows',
        'scope': 'Accepted Git objects only, not mutable implementation or whole repository.'})
    write('baseline-commands.json', commands)
    write('baseline-receipt.json', {
        'schema_version': 1, 'at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'independent-assertions-frozen-awaiting-implementation-handoff',
        'accepted_revision': REVISION, 'selected_source_sha256': source_digest,
        'selection_path': SELECTION_PATH, 'selection_sha256': SELECTION_SHA256,
        'command': [sys.executable, str(pathlib.Path(__file__).resolve())],
        'collector_sha256': digest(pathlib.Path(__file__).read_bytes()),
        'tool_versions': {'python': platform.python_version(), 'git': git_version},
        'product_working_tree_files_read': [], 'mutable_implementation_packet_read': False,
        'producer_or_product_code_executed': False,
        'compiler_native_capture_ui_device_or_process_discovery_commands': [],
        'future_execution_requires': 'Root frozen implementation handoff and verified exact source hashes',
        'cleanup': 'Only owned baseline files written; no test, native or capture child started',
        'scope': 'Source-only independent fixture matrix and verification plan, not implementation acceptance.'})
    print(json.dumps({'accepted_revision': REVISION, 'source_files': len(files),
                      'selected_source_sha256': source_digest,
                      'mutable_implementation_accessed': False}, sort_keys=True))


if __name__ == '__main__':
    main()
