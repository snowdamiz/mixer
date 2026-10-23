#!/usr/bin/env python3
"""Original independent consumer probes over the frozen standalone WASI lane."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest():
    paths = list((ROOT / 'vm/src').rglob('*.rs'))
    paths += list((ROOT / 'vm/tests').glob('swift_wasi*.rs'))
    paths += [ROOT / 'vm/Cargo.toml', ROOT / 'vm/Cargo.lock', ROOT / 'docs/swift-wasi-adapter-design.md', ROOT / 'compiler/experiments/fieldlog-reactor/evidence/2026-10-23-qualified/descriptors.json', Path(__file__), OUT / 'wasi-probe/Cargo.toml', OUT / 'wasi-probe/Cargo.lock']
    paths += list((OUT / 'wasi-probe/src').rglob('*.rs'))
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(set(paths)) if p.is_file()}


def main():
    env = dict(os.environ, PATH='/opt/homebrew/opt/rustup/bin:' + os.environ['PATH'], CARGO_TARGET_DIR='/tmp/mixer-span-execution-target')
    frozen = ROOT / 'verification/swift-wasi/evidence/2026-10-23/receipt.json'
    prior = json.loads(frozen.read_text())
    expected = {p['path']: p['sha256'] for p in prior['sourcesAfter']['files'] if p['path'].startswith('vm/src/experimental_wasi/') or p['path'].startswith('vm/tests/swift_wasi')}
    assert len(expected) == 6, 'expected complete four-source/two-integration-test freeze'
    assert all(sha(ROOT / p) == h for p, h in expected.items()), 'WASI lane changed since frozen receipt'
    receipt = {'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'source_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(), 'tools': {}, 'commands': [], 'lane_receipt': str(frozen.relative_to(ROOT)), 'lane_receipt_sha256': sha(frozen), 'wasi_lane_exactly_matches_frozen_receipt': True, 'wasi_frozen_sources': expected, 'environment': {'PATH_prefix': '/opt/homebrew/opt/rustup/bin', 'CARGO_TARGET_DIR': env['CARGO_TARGET_DIR']}, 'scope': 'Independent original public external-consumer host Rust probes for standalone experimental-swift-wasi only. Six tests: 1156 argv range/alias cases; 66 fd-write output offsets; overlapping read-only iovec input; unsigned denied pointers and recoverable errno; zero log capacity and close; cumulative terminal budget and invalid-arg/cancellation replay. No secure random bytes logged, device runs, downloads, new third-party dependencies, production edits, VM WASI admission/execution, full Swift reactor, product release or GA qualification.'}
    for tool, argv in [('cargo', ['cargo', '--version']), ('rustc', ['rustc', '-Vv'])]:
        result = subprocess.run(argv, cwd=ROOT, env=env, text=True, capture_output=True)
        executable = Path(shutil.which(tool, path=env['PATH'])).resolve()
        receipt['tools'][tool] = {'argv': argv, 'executable': str(executable), 'executable_sha256': sha(executable), 'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}
    for label, extra in [('debug', []), ('release', ['--release'])]:
        before = manifest()
        argv = ['cargo', 'test', '--manifest-path', 'verification/next-slice-review/wasi-probe/Cargo.toml'] + extra + ['--', '--nocapture', '--test-threads=1']
        start = time.monotonic()
        result = subprocess.run(argv, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        log = OUT / ('wasi-' + label + '.log'); log.write_bytes(result.stdout)
        after = manifest()
        receipt['commands'].append({'label': label, 'argv': argv, 'cwd': str(ROOT), 'exit_code': result.returncode, 'elapsed_seconds': time.monotonic() - start, 'log': str(log.relative_to(ROOT)), 'log_sha256': sha(log), 'source_files': before, 'source_tree_sha256': hashlib.sha256(json.dumps(before, sort_keys=True, separators=(',', ':')).encode()).hexdigest(), 'source_stable': before == after})
        (OUT / 'wasi-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        assert before == after, 'sources changed during command'
        assert result.returncode == 0, label + ' failed'
        print(label, result.returncode, flush=True)
    receipt.update(completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(), status='PASS: six original independent host external-consumer WASI probes in Debug and Release; no blocking review finding')
    (OUT / 'wasi-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(receipt['status'])


if __name__ == '__main__':
    main()
