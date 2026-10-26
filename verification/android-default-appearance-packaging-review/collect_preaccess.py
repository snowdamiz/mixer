#!/usr/bin/env python3
"""Source-only independent baseline; never imports or runs product code."""
import datetime
import hashlib
import json
import pathlib
import platform
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent / 'preaccess'
SOURCES = {
    'AGENTS.md': [(1, 57)],
    'mixer-product-plan.md': [(332, 342), (661, 675)],
    'cli/Package.swift': [(1, 14)],
    'cli/Sources/MixerCLI/main.swift': [(78, 85)],
    'cli/Sources/MixerBuild/ProjectGenerator.swift': [(11, 66), (240, 253)],
    'cli/Sources/MixerBuild/AndroidProject.swift': [(27, 105), (131, 144), (179, 208)],
    'cli/Sources/MixerBuild/ProcessRunner.swift': [(1, 37)],
    'cli/Sources/MixerBuild/Configuration.swift': [(76, 134)],
    'cli/Sources/MixerBuild/Resources/android-build.py': [(207, 245), (280, 330)],
    'cli/Tests/MixerBuildTests/AndroidProjectTests.swift': [(1, 77)],
    'sdk/Package.swift': [(1, 28)],
    'sdk/Sources/MixerUI/AppearanceDefaultV2.swift': [(1, 4), (7, 11)],
    'sdk/Sources/MixerUI/AppearanceDescriptorV2.swift': [(1, 38), (821, 861)],
    'native/android/app/src/dev/mixer/android/InstalledAppearanceV2.java': [(11, 63)],
    'native/android/app/src/dev/mixer/android/MixerActivity.java': [(1, 17)],
    'native/android/app/src/dev/mixer/android/NativeEnvironmentV2.java': [(69, 75), (125, 130)],
    'docs/android-public-appearance-routing-proposal.md': [(1, 126)],
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    commands = []
    def command(argv):
        completed = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=15, check=False)
        row = {'argv': argv, 'exit_code': completed.returncode,
               'stdout': completed.stdout, 'stderr': completed.stderr}
        commands.append(row)
        if completed.returncode:
            raise RuntimeError('Source-metadata command failed: ' + repr(argv))
        return completed.stdout.strip()
    revision = command(['git', 'rev-parse', 'HEAD'])
    git_version = command(['git', '--version'])
    rg_version = command(['rg', '--version'])
    paths = []
    excerpts = []
    for name, ranges in SOURCES.items():
        path = ROOT / name
        data = path.read_bytes()
        paths.append({'path': name, 'bytes': len(data), 'sha256': sha(data)})
        lines = data.decode().splitlines()
        excerpts.append('\nFILE ' + name + '\n')
        for start, end in ranges:
            excerpts.append('RANGE ' + str(start) + '-' + str(min(end, len(lines))) + '\n')
            excerpts.extend(str(index) + ': ' + lines[index - 1] + '\n'
                            for index in range(start, min(end, len(lines)) + 1))
    paths.sort(key=lambda row: row['path'])
    selected = sha(''.join(row['path'] + '\0' + row['sha256'] + '\n' for row in paths).encode())
    write('source-manifest.json', {
        'revision': revision, 'files': paths, 'selected_source_sha256': selected,
        'digest_definition': 'SHA256 of sorted UTF8 path + NUL + lowercase file SHA256 + LF rows',
        'scope': 'Explicit public-contract source selection only; not whole repository or immutable build attestation.'})
    (OUT / 'source-excerpts.txt').write_text(''.join(excerpts))
    write('commands.json', commands)
    write('receipt.json', {
        'schema_version': 1,
        'recorded_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'phase': 'independent-preaccess-baseline',
        'status': 'source-observations-only-awaiting-frozen-proposal',
        'source_revision': revision,
        'selected_source_sha256': selected,
        'command': [sys.executable, str(pathlib.Path(__file__).resolve())],
        'collector_sha256': sha(pathlib.Path(__file__).read_bytes()),
        'tool_versions': {'python': platform.python_version(), 'git': git_version, 'ripgrep': rg_version},
        'product_or_compiler_commands_run': [],
        'native_runtime_capture_ui_device_or_process_discovery_commands_run': [],
        'producer_inputs_read': [],
        'unread_until_root_frozen_handoff': [
            'docs/android-default-appearance-packaging-proposal.md',
            'verification/android-default-appearance-packaging-proposal/**'],
        'excluded': ['frozen hosted inspector', 'hosted authority', 'WorkerV2', 'broad local hosted harness',
                     'Patch/Skip implementation, generated sources, tests, fixtures, dependencies'],
        'scope': 'Public-source reading, hashing, excerpts and review obligations only. No implementation or executable product acceptance.',
        'pending': ['Frozen producer proposal review', 'Host and cross-build verification for a future implementation',
                    'Native runtime and UI qualification', 'Physical phone matrix', 'External immutable FieldLog packages',
                    'Signing, OTA, release and GA qualification'],
        'cleanup': 'Collector creates only owned review files; no native, capture or disposable test instances started.'})
    print(json.dumps({'phase': 'preaccess', 'revision': revision, 'selected_source_sha256': selected,
                      'files': len(paths), 'product_or_compiler_commands_run': 0}, sort_keys=True))


if __name__ == '__main__':
    main()
