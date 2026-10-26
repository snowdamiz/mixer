#!/usr/bin/env python3
"""One exact corrected runner invocation under hostile inherited hooks."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).absolute().parent
RUNNER_SHA = 'e531311facb7b38967d3b904b26e92ff3f6c4dc7444c856cd799b70a1d91373b'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    runner = HERE / 'correction-2-copy/check_cache_state.py'
    assert sha(runner) == RUNNER_SHA
    guards = json.loads((HERE / 'evidence/correction-2-guards-complete/receipt.json').read_bytes())
    assert guards['passed']
    evidence = HERE / 'evidence/full-invocation'
    evidence.mkdir(exist_ok=False)
    foreign = evidence / 'hostile-inherited-temp'
    foreign.mkdir()
    sentinel = foreign / 'sentinel.txt'
    sentinel.write_text('No child temporary or capture output may enter this directory.\n')
    before = [{'path': p.name, 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in foreign.iterdir()]
    hostile = {
        'TMPDIR': str(foreign), 'TMP': str(foreign), 'TEMP': str(foreign),
        'RUSTFLAGS': '--not-a-real-rust-option', 'RUST_MIN_STACK': '1',
        'RUSTC_WRAPPER': str(evidence / 'must-not-run-wrapper'),
        'RUSTC_WORKSPACE_WRAPPER': str(evidence / 'must-not-run-workspace-wrapper'),
        'RUST_TEST_THREADS': '999', 'RUST_TEST_SHUFFLE': '1', 'RUST_TEST_SHUFFLE_SEED': '2749',
        'RUST_TEST_RUN_IGNORED': '1', 'RUSTUP_AUTO_INSTALL': '1',
        'CARGO_ENCODED_RUSTFLAGS': '--not-a-real-rust-option',
        'MIXER_CACHE_FIXTURE_EVIDENCE': str(foreign), 'MIXER_REVIEW_SCRATCH': str(foreign),
        'REVIEW_SCRATCH': str(foreign),
    }
    environment = dict(os.environ)
    environment.update(hostile)
    output = runner.parent / 'runs/independent-rust-1-99-full'
    assert not output.exists()
    argv = [sys.executable, '-B', str(runner), '--out', str(output), '--rustc',
            '/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc']
    receipt = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'argv': argv,
        'cwd': str(HERE), 'python': sys.version, 'script_sha256': sha(Path(__file__)),
        'runner_sha256': RUNNER_SHA, 'guard_receipt_sha256': sha(HERE / 'evidence/correction-2-guards-complete/receipt.json'),
        'hostile_inherited_environment': hostile, 'foreign_directory_before': before,
        'runner_limits': {'active_seconds': 600, 'cleanup_seconds': 60, 'child_seconds': 60},
        'normal_full_invocation_count': 1, 'native_or_process_inventory_started': False}
    (evidence / 'launch.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
    started = time.monotonic()
    with (evidence / 'runner.stdout').open('xb') as stdout, (evidence / 'runner.stderr').open('xb') as stderr:
        process = subprocess.Popen(argv, cwd=HERE, env=environment, stdout=stdout, stderr=stderr,
                                   start_new_session=True)
        receipt['pid'] = process.pid
        receipt['pgid'] = process.pid
        (evidence / 'launch.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
        process.wait()
    after = [{'path': p.name, 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in foreign.iterdir()]
    receipt.update(exit=process.returncode, child_returned=True,
        elapsed_seconds=time.monotonic()-started, ended=datetime.now(timezone.utc).isoformat(),
        stdout_sha256=sha(evidence / 'runner.stdout'), stderr_sha256=sha(evidence / 'runner.stderr'),
        foreign_directory_after=after, foreign_directory_unchanged=before == after,
        runner_unchanged=sha(runner) == RUNNER_SHA, runner_receipt=str(output / 'receipt.json'))
    if (output / 'receipt.json').exists():
        receipt['runner_receipt_sha256'] = sha(output / 'receipt.json')
        receipt['runner_status'] = json.loads((output / 'receipt.json').read_bytes())['status']
    (evidence / 'launch.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
    print(json.dumps({k: receipt.get(k) for k in ('exit', 'runner_status', 'elapsed_seconds',
        'foreign_directory_unchanged', 'runner_unchanged', 'runner_receipt')}))
    assert process.returncode == 0 and receipt.get('runner_status') == 'passed-host-fixture-check'
    assert before == after and receipt['runner_unchanged']

if __name__ == '__main__':
    main()
