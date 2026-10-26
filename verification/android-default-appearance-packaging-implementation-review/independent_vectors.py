#!/usr/bin/env python3
"""Independent host adversarial vectors against the exact frozen driver."""
import argparse
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import shutil
import socket
import signal
import subprocess
import sys
import tempfile
import warnings
import zipfile
from unittest import mock

BASE = pathlib.Path(__file__).resolve().parent
DRIVER = BASE / 'frozen-source/cli/Sources/MixerBuild/Resources/android-build.py'
SPEC = importlib.util.spec_from_file_location('independent_frozen_android_driver', DRIVER)
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)
SKIP = {'.build', '.git', '.swiftpm', 'node_modules', '.gradle', '.mixer', 'target', '.DS_Store'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def tree(path):
    rows = []
    for base, dirs, names in os.walk(path, followlinks=False):
        dirs[:] = sorted(name for name in dirs if name not in SKIP)
        for name in sorted(names):
            item = pathlib.Path(base) / name
            if name in SKIP or name == '.env' or (name.startswith('.env.') and name != '.env.example') or item.suffix.lower() in {'.pem', '.key', '.p12', '.pfx', '.mobileprovision', '.keystore', '.jks'}:
                continue
            assert item.is_file() and not item.is_symlink(), str(item)
            rows.append((item.relative_to(path).as_posix(), sha(item.read_bytes())))
    return sha(''.join(name + '\0' + value + '\n' for name, value in sorted(rows)).encode())


class Boundary(Exception):
    pass


class Fixture:
    def __init__(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='mr-', dir='/tmp')
        self.root = pathlib.Path(self.temporary.name).resolve()
        self.adapter = self.root / 'Generated/MixerAndroid'
        self.sdk = self.root / 'Generated/MixerSDK'
        self.descriptor = self.adapter / 'app/assets/MixerAppearanceV2/descriptor.json'
        self.java = self.adapter / 'app/src/dev/mixer/android/AuthoredToggleInputV2.java'
        self.descriptor.parent.mkdir(parents=True)
        self.java.parent.mkdir(parents=True)
        self.sdk.mkdir(parents=True)
        (self.root / 'Resources').mkdir()
        self.descriptor.write_bytes(b'independent layout bytes')
        self.java.write_bytes(b'owned source-lock marker')
        (self.sdk / 'sdk-source.swift').write_bytes(b'owned SDK lock marker')
        config = {'schema': 1, 'name': 'ReviewApp', 'application': 'dev.mixer.review', 'language': 'swift',
                  'targets': ['android'], 'toolchainLock': 'mixer.lock', 'capabilities': [],
                  'updates': {'activation': 'cold-start', 'compatibility': 'exact-runtime-fingerprint',
                              'requireArtifactSignature': True, 'requireAssignmentSignature': True}}
        (self.root / 'mixer.yml').write_text(json.dumps(config))
        self.relock()

    def relock(self):
        value = {'schema': 1, 'sdkDigest': tree(self.sdk),
                 'android': {'adapterDigest': tree(self.adapter), 'toolchain': {}}}
        (self.root / 'mixer.lock').write_text(json.dumps(value))

    def close(self):
        self.temporary.cleanup()


def digest_files(path):
    return {item.relative_to(path).as_posix(): sha(item.read_bytes())
            for item in sorted(path.rglob('*')) if item.is_file() and not item.is_symlink()}


def subprocess_rejection(fixture, case, logs, expected_substring=None):
    output = fixture.root / '.mixer/android-build'
    output.mkdir(parents=True)
    for name in ['ReviewApp-unsigned.apk', 'build-receipt.json', 'keep.txt']:
        (output / name).write_bytes(('owned output sentinel ' + name).encode())
    before = digest_files(output)
    marker = fixture.root / 'tool-was-called'
    fake = fixture.root / 'fake-swift'
    fake.write_text('#!/bin/sh\n: > ' + str(marker) + '\nexit 23\n')
    fake.chmod(0o700)
    environment = os.environ.copy()
    environment['MIXER_SWIFT'] = str(fake)
    argv = [sys.executable, '-B', str(DRIVER), 'build', str(fixture.root)]
    child = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                             env=environment, start_new_session=True)
    try:
        child_stdout, child_stderr = child.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        try: os.killpg(child.pid, signal.SIGTERM)
        except ProcessLookupError: pass
        try: child.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            try: os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            child.communicate(timeout=2)
        raise
    try:
        os.killpg(child.pid, 0)
    except ProcessLookupError:
        pass
    else:
        try: os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError: pass
        raise AssertionError('Owned group remains after driver return')
    completed = subprocess.CompletedProcess(argv, child.returncode, child_stdout, child_stderr)
    (logs / (case + '.stdout')).write_text(completed.stdout)
    (logs / (case + '.stderr')).write_text(completed.stderr)
    assert completed.returncode == 1, (case, completed.returncode, completed.stdout, completed.stderr)
    assert 'Traceback' not in completed.stderr, (case, completed.stderr)
    if expected_substring:
        assert expected_substring in completed.stderr, (case, completed.stderr)
    assert not marker.exists(), case + ': tool executed'
    assert digest_files(output) == before, case + ': output sentinel changed'
    return {'argv': argv, 'exit_code': completed.returncode, 'deadline_seconds': 5,
            'stderr': str((logs / (case + '.stderr')).relative_to(BASE)),
            'stdout': str((logs / (case + '.stdout')).relative_to(BASE)),
            'output_sentinels_unchanged': True, 'tool_attempt_sentinel_absent': True,
            'private_owned_group_absent_on_completion': True}


def mutate(fixture, identifier):
    descriptor = fixture.descriptor
    assets = descriptor.parent.parent
    if identifier == 'A01': shutil.rmtree(assets)
    elif identifier == 'A02': shutil.rmtree(descriptor.parent)
    elif identifier == 'A03': descriptor.unlink()
    elif identifier == 'A04': descriptor.rename(descriptor.with_name('descriptor-renamed.json'))
    elif identifier == 'A05': descriptor.write_bytes(b'')
    elif identifier == 'A06': descriptor.write_bytes(b'x' * 65537)
    elif identifier == 'A07':
        with descriptor.open('wb') as stream: stream.truncate(1024 * 1024 * 1024)
    elif identifier == 'A08': descriptor.unlink(); descriptor.mkdir()
    elif identifier in {'A09', 'A10'}:
        descriptor.unlink()
        target = fixture.root / ('outside-sentinel' if identifier == 'A09' else 'absent')
        if identifier == 'A09': target.write_bytes(b'preserve outside sentinel')
        descriptor.symlink_to(target)
    elif identifier in {'A11', 'A12', 'A13'}:
        path = {'A11': assets, 'A12': descriptor.parent, 'A13': fixture.adapter / 'app'}[identifier]
        moved = path.with_name(path.name + '-moved')
        path.rename(moved); path.symlink_to(moved, target_is_directory=True)
    elif identifier == 'A14': descriptor.unlink(); os.mkfifo(descriptor)
    elif identifier in {'A15', 'A16', 'A17', 'A18', 'A19'}:
        names = {'A15': ['extra.bin'], 'A16': ['.hidden'], 'A17': ['.DS_Store'],
                 'A18': ['.env', '.env.local'], 'A19': ['extra.pem']}[identifier]
        for name in names: (descriptor.parent / name).write_bytes(b'extra')
    elif identifier == 'A20':
        path = descriptor.parent / '.build'; path.mkdir(); (path / 'masked').write_bytes(b'extra')
    elif identifier == 'A21': (descriptor.parent / 'empty-extra').mkdir()
    elif identifier == 'A22': os.mkfifo(descriptor.parent / 'extra-fifo')
    elif identifier == 'A23':
        endpoint = socket.socket(socket.AF_UNIX)
        endpoint.bind(str(descriptor.parent / 'extra-socket'))
        return endpoint
    else: raise AssertionError(identifier)
    return None


def zip_bytes(entries):
    data = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)
        with zipfile.ZipFile(data, 'w') as archive:
            for name, value in entries: archive.writestr(name, value)
    data.seek(0)
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    arguments = parser.parse_args()
    out = pathlib.Path(arguments.output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    logs = out / 'logs'; logs.mkdir()
    results = {}
    failures = []
    def record(identifier, action):
        try:
            detail = action()
            results[identifier] = {'status': 'passed', 'detail': detail}
        except Exception as error:
            results[identifier] = {'status': 'failed', 'error': type(error).__name__ + ': ' + str(error)}
            failures.append(identifier)
        (out / 'vectors.json').write_text(json.dumps(results, indent=2, sort_keys=True) + '\n')
    for number in range(1, 24):
        identifier = 'A' + str(number).zfill(2)
        def case(identifier=identifier):
            fixture = Fixture(); endpoint = None
            try:
                endpoint = mutate(fixture, identifier)
                outside = fixture.root / 'outside-sentinel'
                outside_before = outside.read_bytes() if outside.exists() else None
                with mock.patch.object(BUILD, 'source_tree', side_effect=AssertionError('source hash reached before asset admission')), \
                     mock.patch.object(BUILD, 'inspect', side_effect=AssertionError('tools reached before asset admission')):
                    try: BUILD.build(fixture.root)
                    except RuntimeError: pass
                    else: raise AssertionError('invalid asset accepted')
                assert not (fixture.root / '.mixer').exists()
                detail = subprocess_rejection(fixture, identifier, logs)
                if outside_before is not None: assert outside.read_bytes() == outside_before
                return {'before_source_hash_and_tools': True, **detail}
            finally:
                if endpoint is not None: endpoint.close()
                fixture.close()
        record(identifier, case)
    for identifier, size in [('A24', 1), ('A25', 65536), ('A26', 2)]:
        def boundary(identifier=identifier, size=size):
            fixture = Fixture()
            try:
                value = b'{}' if identifier == 'A26' else b'x' * size
                fixture.descriptor.write_bytes(value); fixture.relock()
                assert BUILD.appearance_input(fixture.adapter) == value
                if identifier == 'A26':
                    with mock.patch.object(BUILD, 'inspect', side_effect=Boundary('owned stop before real tools')) as probe:
                        try: BUILD.build(fixture.root)
                        except Boundary: pass
                        else: raise AssertionError('owned tools boundary not reached')
                        assert probe.call_count == 1
                return {'bytes': len(value), 'layout_admitted': True, 'semantic_claim': False,
                        'recomputed_unauthenticated_lock': True}
            finally: fixture.close()
        record(identifier, boundary)
    for identifier in ['L01', 'L02', 'L03', 'L04']:
        def lock_case(identifier=identifier):
            details = []
            for variant in (['remove', 'rename'] if identifier == 'L03' else ['edit']):
                fixture = Fixture()
                try:
                    path = {'L01': fixture.descriptor, 'L02': fixture.java, 'L03': fixture.java,
                            'L04': fixture.sdk / 'sdk-source.swift'}[identifier]
                    if variant == 'remove': path.unlink()
                    elif variant == 'rename': path.rename(path.with_suffix('.renamed'))
                    else: path.write_bytes(b'changed independent bytes')
                    details.append(subprocess_rejection(fixture, identifier + '-' + variant, logs, 'differs from mixer.lock'))
                finally: fixture.close()
            return {'direct_driver': details, 'cli_lock_layer': 'pending actual fresh CLI consumer'}
        record(identifier, lock_case)
    for identifier, names in [('R01', ['extra.txt']), ('R02', ['.hidden', 'extra.pem'])]:
        def resource_case(identifier=identifier, names=names):
            details = []
            for index, name in enumerate(names):
                fixture = Fixture()
                try:
                    (fixture.root / 'Resources' / name).write_bytes(b'unsupported app resource')
                    details.append(subprocess_rejection(fixture, identifier + '-' + str(index), logs, 'resources cannot be omitted'))
                finally: fixture.close()
            return {'direct_driver': details, 'cli_layer': 'pending actual fresh CLI consumer'}
        record(identifier, resource_case)
    expected = b'locked vector bytes'
    asset = 'assets/MixerAppearanceV2/descriptor.json'
    valid = [(asset, expected), ('classes.dex', b'owned DEX marker')]
    cases = {
        'Z01': valid, 'Z02': [('classes.dex', b'dex')], 'Z03': [('assets/renamed.json', expected)],
        'Z04': valid + [(asset, expected)], 'Z05': valid + [(asset, b'wrong')],
        'Z06': valid + [('assets/extra.bin', b'extra')], 'Z07': valid + [('assets/extra/', b'')],
        'Z08': [(asset, b'X' * len(expected))], 'Z09': [(asset, expected[:-1])],
        'Z10': valid + [('classes.dex', b'extra')],
    }
    for identifier, entries in cases.items():
        def archive_case(identifier=identifier, entries=entries):
            data = zip_bytes(entries)
            (out / (identifier + '.zip')).write_bytes(data.getvalue())
            with zipfile.ZipFile(data) as archive:
                try: result = BUILD.appearance_archive(archive, expected)
                except RuntimeError:
                    assert identifier != 'Z01', 'valid singleton rejected'
                    return {'rejected': True, 'members': [name for name, _ in entries]}
                assert identifier == 'Z01', 'invalid ZIP accepted'
                assert result['bytes'] == len(expected) and result['sha256'] == sha(expected)
                return {'rejected': False, 'identity': result}
        record(identifier, archive_case)
    summary = {'schema_version': 1, 'status': 'passed' if not failures else 'failed',
               'cases': len(results), 'failures': failures, 'results': results,
               'driver_sha256': sha(DRIVER.read_bytes()),
               'scope': 'Independent host layout/lock/ZIP vectors only; actual CLI and consumer vectors recorded separately.',
               'temporary_fixtures_cleanup': 'Every fixture context closed; no native/capture processes started.'}
    (out / 'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'cases': len(results), 'failures': failures, 'status': summary['status']}, sort_keys=True))
    return bool(failures)


if __name__ == '__main__':
    raise SystemExit(main())
