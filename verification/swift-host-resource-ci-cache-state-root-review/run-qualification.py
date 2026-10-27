"""Fresh complete qualification after the fixture-only correction; one shot."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
CI = ROOT / 'verification/swift-cache-state-ci'
RUN = CI / 'runs/host-resource-ci-repair-root-1'
RUSTC = '/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def command(name, argv, timeout):
    start = time.monotonic()
    expired = False
    with (OUT / (name + '.stdout')).open('xb') as stdout, (OUT / (name + '.stderr')).open('xb') as stderr:
        child = subprocess.Popen(argv, cwd=ROOT, stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            code = child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            expired = True
            os.killpg(child.pid, signal.SIGTERM)
            try:
                code = child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                code = child.wait(timeout=5)
    try:
        os.killpg(child.pid, 0)
        gone = False
    except ProcessLookupError:
        gone = True
    row = {'argv': argv, 'exit': code, 'timed_out': expired, 'elapsed_seconds': time.monotonic() - start, 'child_waited': True, 'owned_group_gone': gone, 'stdout_sha256': sha(OUT / (name + '.stdout')), 'stderr_sha256': sha(OUT / (name + '.stderr'))}
    with (OUT / (name + '.command.json')).open('x') as stream:
        json.dump(row, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'phase': name, **row}), flush=True)
    assert code == 0 and not expired and gone, name
    return row

def main():
    assert not RUN.exists(), 'Fresh run required'
    integration = json.loads((OUT / 'integration.json').read_bytes())
    for path, expected in integration['after'].items():
        target = ROOT / path
        assert target.stat().st_size == expected['bytes'] and sha(target) == expected['sha256']
    rows = [command('runner-controls', [sys.executable, '-B', str(CI / 'test_runner.py'), '-v'], 60)]
    rows.append(command('full-fixture', [sys.executable, '-B', str(CI / 'check_cache_state.py'), '--rustc', RUSTC, '--out', str(RUN)], 690))
    receipt = json.loads((RUN / 'receipt.json').read_bytes())
    assert receipt['status'] == 'passed' and receipt['errors'] == []
    assert receipt['cleanup']['removed'] and receipt['cleanup']['groups_returned']
    result = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'status': 'complete-host-fixture-qualification-passed', 'python': sys.version, 'python_sha256': sha(Path(sys.executable).resolve()), 'commands': rows, 'integration_sha256': sha(OUT / 'integration.json'), 'fixture_receipt': str((RUN / 'receipt.json').relative_to(ROOT)), 'fixture_receipt_sha256': sha(RUN / 'receipt.json'), 'receipt_commands': len(receipt['commands']), 'compiler_identity': receipt['rustc'], 'original_CI_failure_remains_failed': True, 'fresh_Rust_1_98_1_CI_pending': True, 'native_runtime_or_GA': False}
    with (OUT / 'qualification.json').open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result), flush=True)

if __name__ == '__main__':
    main()
