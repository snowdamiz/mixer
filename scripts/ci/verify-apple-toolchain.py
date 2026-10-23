#!/usr/bin/env python3
"""Verify an explicitly selected installed Xcode before CI builds any package.

This records trusted hosted-runner tools. It does not attest an entire SDK,
qualify a device, modify global xcode-select, or authorize product artifacts.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile


def swift_version(output):
    match = re.search(r'\bSwift version (\d+)\.(\d+)(?:\.(\d+))?(?=\s|$)', output)
    if not match:
        raise ValueError('Cannot identify the installed Swift compiler version')
    return tuple(int(value or 0) for value in match.groups())


def verify_versions(xcode_output, swift_output, xcode_version, xcode_build, minimum=(6, 2, 0)):
    expected = f'Xcode {xcode_version}\nBuild version {xcode_build}'
    if xcode_output.strip() != expected:
        raise ValueError(f'Selected Xcode does not match the pinned version/build: {xcode_output.strip()}')
    actual = swift_version(swift_output)
    if actual < minimum:
        raise ValueError(f'Swift {actual} does not meet the required minimum {minimum}')
    return actual


def run(command, environment):
    # Version/SDK probes are fixed trusted commands. Spool diagnostics and cap
    # result reads so accidental output cannot allocate unbounded memory.
    with tempfile.TemporaryFile() as stream:
        result = subprocess.run([str(value) for value in command], env=environment,
                                stdout=stream, stderr=subprocess.STDOUT, timeout=30)
        stream.seek(0)
        output = stream.read(262145)
    if len(output) > 262144:
        raise ValueError('Toolchain probe exceeded its output limit')
    text = output.decode('utf-8')
    if result.returncode:
        raise ValueError(f'Toolchain probe {command[0]} exited {result.returncode}: {text}')
    return text.strip()


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            value.update(block)
    return value.hexdigest()


def probe(developer, xcode_version, xcode_build):
    developer = Path(developer).absolute()
    if not developer.is_dir() or '\n' in str(developer) or '\r' in str(developer):
        raise ValueError('Pinned Xcode developer directory is not installed')
    environment = dict(os.environ, DEVELOPER_DIR=str(developer),
                       TOOLCHAINS='com.apple.dt.toolchain.XcodeDefault')
    xcode_output = run(['/usr/bin/xcodebuild', '-version'], environment)
    swift = Path(run(['/usr/bin/xcrun', '--find', 'swift'], environment))
    if not swift.resolve().is_relative_to(developer.resolve()):
        raise ValueError('Resolved Swift compiler belongs to another Xcode installation')
    swift_output = run([swift, '--version'], environment)
    version = verify_versions(xcode_output, swift_output, xcode_version, xcode_build)
    sdk_versions = {sdk: run(['/usr/bin/xcrun', '--sdk', sdk, '--show-sdk-version'], environment)
                    for sdk in ['macosx', 'iphonesimulator']}
    return {'schema': 1, 'status': 'verified-installed-toolchain',
            'scope': 'host package tests and unsigned simulator build; no device or release qualification',
            'sourceRevision': run(['git', 'rev-parse', 'HEAD'], environment),
            'runnerImageOS': os.environ.get('ImageOS'), 'runnerImageVersion': os.environ.get('ImageVersion'),
            'developerDirectory': str(developer), 'toolchains': environment['TOOLCHAINS'],
            'xcode': xcode_output, 'swift': swift_output, 'swiftVersion': list(version),
            'swiftPath': str(swift), 'swiftSHA256': digest(swift.resolve()),
            'swiftFrontendSHA256': digest(swift.parent/'swift-frontend'),
            'sdkVersions': sdk_versions, 'host': run(['/usr/bin/sw_vers'], environment),
            'probeSHA256': digest(__file__)}, str(swift.parent)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--developer-dir', required=True)
    parser.add_argument('--xcode-version', required=True)
    parser.add_argument('--xcode-build', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    receipt, compiler_directory = probe(args.developer_dir, args.xcode_version, args.xcode_build)
    # Preserve this selection for CLI-generated subprocesses as well as top-level
    # Swift commands. This affects only later steps in the current Actions job.
    if os.environ.get('GITHUB_PATH'):
        with open(os.environ['GITHUB_PATH'], 'a', encoding='utf-8') as path_file:
            path_file.write(compiler_directory+'\n')
    args.output.write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
