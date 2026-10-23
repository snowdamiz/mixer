#!/usr/bin/env python3
"""Independent host cache probes with exact source/artifact bindings, offline."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TARGET = ROOT / 'vm/target/stream-validation-verification'
OWNER_RECEIPT = ROOT / 'verification/span-function-cache/2026-10-23-host/receipt.json'


def sha(content):
    return hashlib.sha256(content).hexdigest()


def snapshot():
    result = {}
    for directory, directories, files in os.walk(ROOT / 'vm'):
        directories[:] = sorted(set(directories) - {'target', 'verification', '__pycache__'})
        for name in sorted(files):
            if name != '.DS_Store':
                path = Path(directory) / name
                result[path.relative_to(ROOT).as_posix()] = sha(path.read_bytes())
    return dict(sorted(result.items()))


def verify(receipt):
    assert receipt['source_files_sha256'] == snapshot(), 'stale VM source binding'
    for name, expected in receipt['review_input_sha256'].items():
        assert sha((ROOT / name).read_bytes()) == expected, 'stale review input: ' + name
    for command in receipt['commands']:
        path = ROOT / command['output']
        assert sha(path.read_bytes()) == command['output_sha256'], 'changed command log'
        assert command['exit_code'] == 0, 'failed command in receipt'
    assert receipt['status'] == 'passed', 'review receipt did not pass'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', default='2026-10-23-host')
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    assert args.name and all(c.isascii() and (c.isalnum() or c in '-_') for c in args.name)
    out = HERE / args.name
    if args.verify:
        verify(json.loads((out / 'receipt.json').read_text()))
        print('Review receipt source/input/log bindings verified; host cache scope only.')
        return
    out.mkdir(exist_ok=False)
    build = HERE / '.build' / args.name
    build.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ)
    env['PATH'] = '/opt/homebrew/opt/rustup/bin:' + env.get('PATH', '')
    env['CARGO_TARGET_DIR'] = str(TARGET)
    source = snapshot()
    owner = json.loads(OWNER_RECEIPT.read_text())
    expected = owner['source_files_sha256']
    changed = {name: {'owner': expected[name], 'current': source.get(name)}
               for name in expected if source.get(name) != expected[name]}
    extra = sorted(set(source) - set(expected))
    # Root explicitly disclosed this additive, uncompiled contract header after
    # the cache candidate seal. Every original cache-candidate byte must match.
    assert not changed, 'implementation receipt source is stale: ' + repr(changed)
    assert set(extra) <= {'vm/include/mixer_vm_guest_ui.h'}, 'unexpected added VM inputs'
    accepted = json.loads((ROOT / 'verification/span-function-cache/accepted-design.json').read_text())
    assert accepted['status'] == 'root-accepted'
    assert sha((ROOT / accepted['path']).read_bytes()) == accepted['sha256'], 'accepted design drift'
    commands = []
    artifacts = []
    inputs = [HERE / 'run.py', HERE / 'probes.rs', OWNER_RECEIPT,
              ROOT / accepted['path'], ROOT / 'verification/span-function-cache/accepted-design.json']
    receipt = {
        'schema': 'mixer-span-function-cache-independent-review-v1',
        'status': 'running',
        'began_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'source_files_sha256': source,
        'source_manifest_sha256': sha(json.dumps(source, sort_keys=True).encode()),
        'implementation_candidate_manifest_sha256': owner['source_manifest_sha256'],
        'additional_vm_files_outside_cache_candidate': extra,
        'review_input_sha256': {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in inputs},
        'commands': commands, 'artifacts': artifacts,
        'target': str(TARGET),
        'scope': 'Independent public API probes and source review of nondefault host decoded cache; no execution bridge',
        'limitations': ['Host macOS Rust probes only; concurrency is a finite stress sample, not a formal race proof',
                        'Requested allocator bytes and counters are not process RSS',
                        'No guest execution, full Swift, WASI, physical iOS/Android, runtime trap/close integration',
                        'No native ABI/signing/store/customer/published-package/OTA/GA qualification'],
    }

    def run(name, argv):
        start = time.monotonic()
        p = subprocess.run(argv, cwd=ROOT, env=env, text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        log = out / (name + '.log')
        log.write_text(p.stdout)
        commands.append({'name': name, 'argv': argv, 'exit_code': p.returncode,
                         'elapsed_host_seconds': round(time.monotonic() - start, 6),
                         'output': log.relative_to(ROOT).as_posix(), 'output_sha256': sha(log.read_bytes())})
        print(name + ': ' + ('passed' if p.returncode == 0 else 'FAILED'), flush=True)
        if p.returncode:
            raise RuntimeError('command failed: ' + name)
        return p.stdout

    try:
        run('rustc-version', ['rustc', '--version', '--verbose'])
        run('cargo-version', ['cargo', '--version'])
        run('python-version', ['python3', '--version'])
        run('host-version', ['uname', '-a'])
        for profile, options in [('debug', []), ('release', ['--release'])]:
            output = run(profile + '-artifact-binding', ['cargo', 'test', '--offline', '--manifest-path',
                'vm/Cargo.toml', '--features', 'experimental-function-cache', *options, '--no-run',
                '--test', 'span_function_cache', '--message-format=json'])
            records = [json.loads(line) for line in output.splitlines() if line.startswith('{')]
            library_records = [r for r in records if r.get('reason') == 'compiler-artifact'
                               and r['target']['name'] == 'mixer_vm'
                               and 'rlib' in r['target']['crate_types']
                               and 'experimental-function-cache' in r['features']]
            assert len(library_records) == 1, 'missing exact feature rlib artifact'
            library = Path(next(f for f in library_records[0]['filenames'] if f.endswith('.rlib')))
            library_sha = sha(library.read_bytes())
            assert snapshot() == source, 'VM source changed before probe compile'
            executable = build / ('probes-' + profile)
            run(profile + '-compile', ['rustc', '--edition=2021', '-D', 'warnings',
                '-C', 'opt-level=' + ('0' if profile == 'debug' else '3'),
                '-C', 'overflow-checks=yes', '-C', 'panic=unwind', str(HERE / 'probes.rs'),
                '--extern', 'mixer_vm=' + str(library), '-L', 'dependency=' + str(library.parent),
                '-o', str(executable)])
            assert sha(library.read_bytes()) == library_sha, 'feature rlib changed while linking'
            run(profile + '-probes', [str(executable)])
            artifacts.append({'profile': profile, 'library': str(library), 'library_sha256': library_sha,
                'cargo_artifact': library_records[0], 'probe_binary_sha256': sha(executable.read_bytes())})
        assert snapshot() == source, 'VM source changed during review probes'
        receipt['status'] = 'passed'
    except Exception as error:
        receipt['status'] = 'failed'
        receipt['failure'] = str(error)
        raise
    finally:
        receipt['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        receipt['source_stable'] = snapshot() == source
        (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    verify(receipt)
    print('receipt: ' + str(out / 'receipt.json'))


if __name__ == '__main__':
    main()
