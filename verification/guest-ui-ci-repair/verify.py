#!/usr/bin/env python3
"""Bounded fixture repair evidence. Reuses the already-qualified native archive."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
ARCHIVE = ROOT / 'experimental-capability-runtime/build-verification/local/guest-ui-1adb25c-v2/host/lib/libmixer_vm_capability_experimental.a'
ARCHIVE_SHA = '4d3b6dc36ea034d5604299752d560cbbc0615002b6b5ef4e5c25bbb3cb7c6120'
INCLUDE = ARCHIVE.parent.parent / 'include'
RUNTIME = ROOT / 'experimental-capability-runtime/Tests/MixerExperimentalCapabilityRuntimeTests'
SIGNED = ROOT / 'capability-activation/Tests/MixerCapabilityActivationTests/GuestUISignedProgram.swift'
C_SOURCE = ROOT / 'experimental-capability-runtime/build-tests/guest_ui.c'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(name, command, entries):
    command = [str(value) for value in command]
    result = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log = HERE / (name + '.log')
    log.write_text(result.stdout)
    entries.append({'name': name, 'command': command, 'exit_code': result.returncode,
                    'log': str(log.relative_to(ROOT)), 'log_sha256': sha(log)})
    print(name, result.returncode, flush=True)
    if result.returncode:
        raise RuntimeError(result.stdout)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['before', 'after'])
    args = parser.parse_args()
    assert sha(ARCHIVE) == ARCHIVE_SHA
    phase = args.phase
    build = HERE / '.build' / phase
    output = build / 'output'
    output.mkdir(parents=True, exist_ok=True)
    sources = [HERE / 'before/GuestProgram.swift', HERE / 'before/GuestUIProgram.swift', HERE / 'before/GuestUISignedProgram.swift'] if phase == 'before' else [RUNTIME / 'GuestProgram.swift', RUNTIME / 'GuestUIProgram.swift', SIGNED]
    c_source = HERE / 'before/guest_ui.c' if phase == 'before' else C_SOURCE
    commands = []
    record = {'phase': phase, 'observed_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'base': json.loads((HERE / 'before-source.json').read_text()),
              'archive': {'path': str(ARCHIVE.relative_to(ROOT)), 'sha256': sha(ARCHIVE)},
              'sources': [{'path': str(p.relative_to(ROOT)), 'sha256': sha(p)} for p in [*sources, c_source]],
              'commands': commands}
    try:
        run(phase + '-swift-version', ['swiftc', '--version'], commands)
        run(phase + '-clang-version', ['clang', '--version'], commands)
        run(phase + '-swift-compile', ['swiftc', '-parse-as-library', '-swift-version', '6', '-warnings-as-errors', *sources, HERE / 'FixtureParity.swift', '-o', build / 'swift-parity'], commands)
        run(phase + '-swift-fixtures', [build / 'swift-parity', output], commands)
        flags = ['clang', '-std=c11', '-Wall', '-Wextra', '-Wmisleading-indentation']
        if phase == 'after':
            flags += ['-Werror']
        flags += ['-mmacosx-version-min=14.0', '-I', INCLUDE]
        run(phase + '-c-compile', [*flags, '-DFIXTURE_SOURCE="' + str(c_source) + '"', HERE / 'c_fixture_parity.c', ARCHIVE, '-o', build / 'c-parity'], commands)
        run(phase + '-c-fixtures', [build / 'c-parity', output], commands)
        if phase == 'after':
            run('after-c-smoke-compile', [*flags, c_source, ARCHIVE, '-o', build / 'c-smoke'], commands)
            run('after-c-smoke', [build / 'c-smoke'], commands)
        files = sorted(output.glob('*.wasm'))
        assert len(files) == 167, len(files)
        record['outputs'] = [{'name': p.name, 'size': p.stat().st_size, 'sha256': sha(p)} for p in files]
        if phase == 'after':
            baseline = json.loads((HERE / 'before.json').read_text())
            assert record['outputs'] == baseline['outputs']
            for file in files:
                assert file.read_bytes() == (HERE / '.build/before/output' / file.name).read_bytes(), file
            record['byte_parity'] = {'status': 'passed', 'modules': len(files), 'comparison': 'full byte arrays and SHA-256',
                                     'scope': 'all 12 runtime modes across 13 initialRevision values, max for two non-overflowing modes, both defaults, all 5 signed modes, both C variants',
                                     'limitation': 'representative UInt64 boundaries and every existing test parameter; not exhaustive over 2^64 values'}
        record['status'] = 'passed'
    except Exception as error:
        record['status'] = 'failed'
        record['error'] = str(error)
        raise
    finally:
        (HERE / (phase + '.json')).write_text(json.dumps(record, indent=2) + '\n')


if __name__ == '__main__':
    main()
