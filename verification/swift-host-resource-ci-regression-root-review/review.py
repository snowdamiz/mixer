"""Root source/custody review and bounded execution of the two changed controls."""
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
PACK = ROOT / 'verification/swift-host-resource-ci-regression'
sha = lambda b: hashlib.sha256(b).hexdigest()

def main():
    freeze = json.loads((PACK / 'freeze.json').read_bytes())
    assert sha((PACK / 'freeze.json').read_bytes()) == '7aab3def0355ba429b015a8449462af36dcac301d03ff2c22a0491a267849c85'
    assert freeze['files_manifest_sha256'] == '6fdfb941fad8fda29a286fc560eeb31658806f2fccfa60164bb2a6ef0b3c1ac8'
    for row in freeze['files']:
        path = PACK / row['path']
        data = path.read_bytes()
        assert path.is_file() and not path.is_symlink()
        assert len(data) == row['bytes'] and sha(data) == row['sha256']
    assert {p.relative_to(PACK).as_posix() for p in PACK.rglob('*') if p.is_file()} == {r['path'] for r in freeze['files']} | {'freeze.json'}
    producer = json.loads((PACK / 'receipt.json').read_bytes())
    for row in producer['selected_python_sources']:
        assert sha((ROOT / row['path']).read_bytes()) == row['sha256']
    source = ROOT / 'scripts/ci/tests/test_analyzer_envelope_runner.py'
    expected = '8eac83b0e1ec6f32f6db5b7103eeaeee10942322f3430ca9dc75f92e79b38f9f'
    assert sha(source.read_bytes()) == expected
    command = [sys.executable, '-B', str(source), '-v',
               'RunnerControls.test_timeout_kills_all_owned_group_members_and_returns_children',
               'RunnerControls.test_unconfirmed_group_disappearance_is_refused_after_clean_child_exit']
    started = time.monotonic()
    timed_out = False
    with (OUT / 'focused.stdout').open('xb') as stdout, (OUT / 'focused.stderr').open('xb') as stderr:
        child = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            code = child.wait(timeout=30)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(child.pid, signal.SIGKILL)
            code = child.wait(timeout=5)
    try:
        os.killpg(child.pid, 0)
        group_gone = False
    except ProcessLookupError:
        group_gone = True
    receipt = {
        'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'command': command, 'python': sys.version,
        'python_sha256': sha(Path(sys.executable).resolve().read_bytes()),
        'source_commit': producer['source_revision'], 'source_tree': producer['base_git_tree'],
        'source_sha256': expected, 'review_script_sha256': sha(Path(__file__).read_bytes()),
        'producer_freeze_sha256': sha((PACK / 'freeze.json').read_bytes()),
        'producer_files_rehashed': len(freeze['files']),
        'elapsed_seconds': time.monotonic() - started, 'exit': code, 'timed_out': timed_out,
        'owned_child_waited': True, 'owned_group_gone': group_gone,
        'stdout_sha256': sha((OUT / 'focused.stdout').read_bytes()),
        'stderr_sha256': sha((OUT / 'focused.stderr').read_bytes()),
        'reviewer_preflight_failure': 'Initial inline preflight compared the file-manifest digest to freeze.json bytes; it failed before writes or child launch. Corrected by independently binding both distinct digests.',
        'scope': 'Test-only fresh-group termination and directly waitable exact child handles; persistent-group refusal preserved. No new-session creation or orphan-reaping behavior claim. Production runner unchanged.',
        'native_runtime_or_GA': False,
    }
    (OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))
    print((OUT / 'focused.stderr').read_text())
    assert code == 0 and not timed_out and group_gone

if __name__ == '__main__':
    main()
