#!/usr/bin/env python3
"""Compare external standalone observations to the frozen 020f909 foundation."""
import datetime
import hashlib
import io
import json
import os
import pathlib
import subprocess
import tarfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = pathlib.Path(__file__).resolve().parent
RUST = pathlib.Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
OUT = BASE / 'standalone-parity'
OUT.mkdir(exist_ok=False)
BASELINE = BASE / '.build/baseline'
BASELINE.mkdir(exist_ok=False)
FROZEN = '020f909f2a32553b79ba7068a1798c85d97426b4'
archive = subprocess.check_output(['git', 'archive', FROZEN, 'vm/src', 'vm/Cargo.toml', 'vm/Cargo.lock'], cwd=ROOT)
with tarfile.open(fileobj=io.BytesIO(archive)) as contents:
    contents.extractall(BASELINE, filter='data')


def digest(path):
    data = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
                bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def tree(source):
    entries = []
    for path in sorted((source / 'vm').rglob('*')):
        if path.is_file():
            entry = digest(path)
            entry['path'] = str(path.relative_to(source))
            entries.append(entry)
    return dict(files=entries, tree_sha256=hashlib.sha256(json.dumps(entries, sort_keys=True, separators=(',', ':')).encode()).hexdigest())


commands = []


def run(label, argv, cwd, env):
    started = time.monotonic()
    result = subprocess.run(list(map(str, argv)), cwd=cwd, env=env, capture_output=True, timeout=60)
    stdout = OUT / (label + '.stdout')
    stderr = OUT / (label + '.stderr')
    stdout.write_bytes(result.stdout)
    stderr.write_bytes(result.stderr)
    commands.append(dict(label=label, argv=list(map(str, argv)), cwd=str(cwd), exit_code=result.returncode,
                         elapsed_seconds=time.monotonic() - started, stdout=digest(stdout), stderr=digest(stderr)))
    print(json.dumps(dict(label=label, exit_code=result.returncode)), flush=True)
    return result


snapshots = {'baseline': BASELINE, 'final': BASE / '.build/final'}
before = {name: tree(source) for name, source in snapshots.items()}
observations = {}
for name, source in snapshots.items():
    target = BASE / '.build' / ('parity-' + name + '-target')
    env = dict(os.environ, PATH=str(RUST) + ':' + os.environ.get('PATH', ''), CARGO_TARGET_DIR=str(target))
    for mode in ['debug', 'release']:
        release = ['--release'] if mode == 'release' else []
        for feature in ['experimental-swift-wasi', 'experimental-swift-reactor']:
            label = name + '-' + mode + '-' + feature
            result = run(label + '-build', [RUST / 'cargo', 'build', '--offline', '--manifest-path', 'vm/Cargo.toml',
                         '--features', feature, '--lib', *release], source, env)
            if result.returncode:
                continue
            binary = OUT / label
            result = run(label + '-compile', [RUST / 'rustc', '--edition', '2021', BASE / 'standalone_parity.rs',
                         '--extern', 'mixer_vm=' + str(target / mode / 'libmixer_vm.rlib'),
                         '-L', 'dependency=' + str(target / mode / 'deps'), '-o', binary], source, env)
            if result.returncode:
                continue
            result = run(label + '-observe', [binary], source, env)
            if result.returncode == 0:
                observations[label] = digest(OUT / (label + '-observe.stdout'))
            binary.unlink(missing_ok=True)
after = {name: tree(source) for name, source in snapshots.items()}
unchanged = before == after
equal = len(observations) == 8 and len({entry['sha256'] for entry in observations.values()}) == 1
(OUT / 'source-manifests.json').write_text(json.dumps(before, indent=2) + '\n')
receipt = dict(observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), baseline_revision=FROZEN,
               source_manifests=digest(OUT / 'source-manifests.json'), source_stable=unchanged,
               source=digest(BASE / 'standalone_parity.rs'), collector=digest(pathlib.Path(__file__)),
               commands=commands, observations=observations, all_observations_equal=equal,
               success=unchanged and equal and all(c['exit_code'] == 0 for c in commands),
               scope='External old standalone constructor/dispatch/layout/usage observations across all 34 descriptors and four argument variants in Debug and Release, WASI-only and reactor-feature builds.',
               limitations=['Native host observations use default denied services; no target reactor execution or physical device qualification.'])
(OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(dict(receipt=str(OUT / 'receipt.json'), success=receipt['success'])), flush=True)
raise SystemExit(0 if receipt['success'] else 1)
