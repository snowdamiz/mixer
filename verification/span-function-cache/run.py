#!/usr/bin/env python3
"""Sealed host-only cache receipt. Reuses the existing Cargo target, offline."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
BASE = 'ac2d2b693db4e2648d161b4fb5975686e5d34393'
FEATURE_LINE = b'experimental-function-cache = ["experimental-stream-validation"]\n'
MODULE_LINES = b'#[cfg(feature = "experimental-function-cache")]\npub mod cache;\n\n'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def manifest():
    paths = [p for p in (ROOT / 'vm').rglob('*') if p.is_file()
             and not {'target', 'verification', '__pycache__'}.intersection(p.relative_to(ROOT / 'vm').parts)
             and p.name != '.DS_Store']
    return {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in sorted(paths)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    if not args.name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in args.name):
        parser.error('name must be an ASCII identifier')
    out = Path(__file__).resolve().parent / args.name
    out.mkdir(exist_ok=False)
    env = dict(os.environ)
    env['PATH'] = '/opt/homebrew/opt/rustup/bin:' + env.get('PATH', '')
    env['CARGO_TARGET_DIR'] = str(ROOT / 'vm/target/stream-validation-verification')
    logs = []
    began = datetime.datetime.now(datetime.timezone.utc).isoformat()
    start = manifest()
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()

    def run(name, argv):
        t = time.monotonic()
        result = subprocess.run(argv, cwd=ROOT, env=env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        log = out / (name + '.log')
        log.write_text(result.stdout)
        logs.append({'name': name, 'argv': argv, 'exit_code': result.returncode,
                     'elapsed_host_seconds': round(time.monotonic() - t, 6),
                     'output': log.relative_to(ROOT).as_posix(),
                     'output_sha256': sha(result.stdout.encode())})
        print(name + ': ' + ('passed' if result.returncode == 0 else 'FAILED'), flush=True)
        if result.returncode:
            (out / 'failed-command.json').write_text(json.dumps(logs, indent=2) + '\n')
            raise SystemExit(result.returncode)
        return result.stdout

    paths = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', BASE, '--',
                                     'vm/src', 'vm/tests', 'vm/include', 'vm/profiles',
                                     'vm/Cargo.toml', 'vm/Cargo.lock',
                                     'contracts/vm-profile-v1.json', 'contracts/vm-session-v1.json'],
                                    cwd=ROOT, text=True).splitlines()
    isolation = {}
    for name in paths:
        old = subprocess.check_output(['git', 'show', BASE + ':' + name], cwd=ROOT)
        current = (ROOT / name).read_bytes()
        if name == 'vm/Cargo.toml':
            assert current.count(FEATURE_LINE) == 1
            current = current.replace(FEATURE_LINE, b'', 1)
        if name == 'vm/src/experimental/mod.rs':
            assert current.count(MODULE_LINES) == 1
            current = current.replace(MODULE_LINES, b'', 1)
        assert current == old, 'frozen existing source changed: ' + name
        isolation[name] = sha(old)
    (out / 'existing-source-isolation.json').write_text(json.dumps({'baseline': BASE, 'files': isolation,
        'only_stripped_snippets': {'vm/Cargo.toml': FEATURE_LINE.decode(), 'vm/src/experimental/mod.rs': MODULE_LINES.decode()},
        'scope': 'Exact source/header/profile isolation; no new native archive build or C executable/symbol receipt.'}, indent=2) + '\n')
    run('version-rustc', ['rustc', '--version', '--verbose'])
    run('version-cargo', ['cargo', '--version'])
    run('version-node', ['node', '--version'])
    run('version-platform', ['uname', '-a'])
    run('format', ['cargo', 'fmt', '--manifest-path', 'vm/Cargo.toml', '--', '--check'])
    cargo = ['cargo', 'test', '--offline', '--manifest-path', 'vm/Cargo.toml']
    for label, flags in [('default-debug', []), ('feature-debug', ['--features', 'experimental-function-cache']),
                         ('default-release', ['--release']), ('feature-release', ['--release', '--features', 'experimental-function-cache'])]:
        run(label, cargo + flags + ['--', '--nocapture'])
    run('feature-development-oracles', cargo + ['--features', 'experimental-function-cache', '--', '--ignored', '--nocapture'])
    for label, flags in [('default', []), ('feature', ['--features', 'experimental-function-cache'])]:
        run('clippy-' + label, ['cargo', 'clippy', '--offline', '--manifest-path', 'vm/Cargo.toml', *flags, '--all-targets', '--', '-D', 'warnings'])
    final = manifest()
    assert final == start, 'VM source changed during receipt; rerun after source freeze'
    receipt = {'schema': 'mixer-span-function-cache-host-receipt-v1', 'began_utc': began,
               'finished_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'head': head,
               'source_files_sha256': start, 'source_manifest_sha256': sha(json.dumps(start, sort_keys=True).encode()),
               'commands': logs, 'target': env['CARGO_TARGET_DIR'], 'network': 'Cargo offline; no dependency or package graph created',
               'scope': 'Host decoded cache and default/feature source/test isolation only; no guest execution bridge',
               'pending': ['execution bridge', 'runtime recursion/indirect execution and trap/close integration', 'WASI',
                           'full Swift profile/admission', 'actual FieldLog execution', 'physical iOS/Android',
                           'C ABI binary symbol and native archive rebuild', 'aggregate session byte admission',
                           'standards/fuzz/security audit', 'published package dogfood', 'OTA/GA']}
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('receipt: ' + str(out / 'receipt.json'), flush=True)


if __name__ == '__main__':
    main()
