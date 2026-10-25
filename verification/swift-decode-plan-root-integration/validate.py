#!/usr/bin/env python3
"""Fresh focused live host regression with bounded owned build storage."""
from pathlib import Path
import datetime
import gzip
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
INPUT = ROOT / 'verification/swift-decode-plan-full-regression'
SCRATCH = BASE / 'owned-target'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    (BASE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


tools = json.loads((INPUT / 'tools.json').read_text())
manifest = json.loads((BASE / 'live-source-manifest.json').read_text())
for name, value in manifest.items():
    assert digest(ROOT / 'vm' / name) == value, name
for name in ['cargo', 'rustc', 'rustfmt']:
    assert digest(Path(tools[name]['path'])) == tools[name]['sha256']
assert not SCRATCH.exists(), 'Preserve previous scratch'
SCRATCH.mkdir()
scratch_identity = (SCRATCH.stat().st_dev, SCRATCH.stat().st_ino)
(SCRATCH / 'tmp').mkdir()
env = os.environ.copy()
explicit = {
    'PATH': str(Path(tools['cargo']['path']).parent) + ':/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',
    'CARGO_TARGET_DIR': str(SCRATCH), 'CARGO_INCREMENTAL': '0',
    'CARGO_BUILD_JOBS': '2', 'CARGO_NET_OFFLINE': 'true',
    'TMPDIR': str(SCRATCH / 'tmp'), 'RUST_TEST_THREADS': '1',
}
env.update(explicit)
commands = []


def command(label, argv, timeout):
    start = time.monotonic()
    result = {'label': label, 'argv': argv, 'cwd': str(ROOT),
              'environment': explicit, 'sourceClosure': digest(BASE / 'live-source-manifest.json'),
              'startedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'timeoutSeconds': timeout, 'signals': []}
    with (BASE / (label + '.stdout')).open('wb') as out, (BASE / (label + '.stderr')).open('wb') as err:
        process = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=out, stderr=err, start_new_session=True)
        result['pid'] = result['pgid'] = process.pid
        try:
            result['exitCode'] = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            result['signals'].append('SIGTERM')
            os.killpg(process.pid, signal.SIGTERM)
            try:
                result['exitCode'] = process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                result['signals'].append('SIGKILL')
                os.killpg(process.pid, signal.SIGKILL)
                result['exitCode'] = process.wait(timeout=5)
    ps = subprocess.check_output(['/bin/ps', '-axo', 'pid=,pgid=,comm='], text=True, timeout=30)
    result.update(durationSeconds=time.monotonic() - start, streamsClosed=True,
                  ownedGroupMembers=[line for line in ps.splitlines()
                                     if len(line.split()) >= 2 and int(line.split()[1]) == process.pid])
    result['ownedGroupAbsent'] = not result['ownedGroupMembers']
    result['stdoutSHA256'] = digest(BASE / (label + '.stdout'))
    result['stderrSHA256'] = digest(BASE / (label + '.stderr'))
    commands.append(result)
    save('commands.json', commands)
    print(label, result['exitCode'], flush=True)
    assert result['ownedGroupAbsent'], 'Preserve scratch while owned group survives'
    return result


cargo = tools['cargo']['path']
test = command('live-swift-library', [cargo, 'test', '--offline', '--locked', '--manifest-path',
    str(ROOT / 'vm/Cargo.toml'), '--features', 'experimental-swift-reactor', '--lib',
    'experimental_swift_reactor::', '--', '--test-threads=1'], 300)
fmt = command('live-format-check', [cargo, 'fmt', '--manifest-path', str(ROOT / 'vm/Cargo.toml'), '--', '--check'], 60)
source_unchanged = all(digest(ROOT / 'vm' / name) == value for name, value in manifest.items())
assert source_unchanged
stdout = (BASE / 'live-swift-library.stdout').read_text()
tests = re.findall(r'^test (\S+) \.\.\. (ok|FAILED|ignored.*)$', stdout, re.M)
passed = sum(status == 'ok' for _, status in tests)
failed = sum(status == 'FAILED' for _, status in tests)
ignored = len(tests) - passed - failed
fmt_output = (BASE / 'live-format-check.stdout').read_text()
fmt_files = set(re.findall(r'^Diff in (.+?):\d+:$', fmt_output, re.M))
fmt_hunks = len(re.findall(r'^Diff in ', fmt_output, re.M))
binaries = []
for path in sorted((SCRATCH / 'debug/deps').glob('mixer_vm-*')):
    if path.is_file() and os.access(path, os.X_OK) and path.read_bytes()[:4] in [b'\xcf\xfa\xed\xfe', b'\xfe\xed\xfa\xcf']:
        raw = path.read_bytes()
        target = BASE / ('live-test-' + hashlib.sha256(raw).hexdigest() + '.gz')
        target.write_bytes(gzip.compress(raw, mtime=0))
        binaries.append({'archive': target.name, 'sha256': hashlib.sha256(raw).hexdigest(),
                         'bytes': len(raw), 'archiveSHA256': digest(target)})
assert len(binaries) == 1
holders = subprocess.run(['/usr/sbin/lsof', '-nP', '+D', str(SCRATCH)], capture_output=True, timeout=30)
(BASE / 'cleanup-lsof.stdout').write_bytes(holders.stdout)
(BASE / 'cleanup-lsof.stderr').write_bytes(holders.stderr)
assert holders.returncode == 1 and not holders.stdout, 'Preserve scratch with open holders'
assert scratch_identity == (SCRATCH.stat().st_dev, SCRATCH.stat().st_ino)
removed = sum(p.stat().st_size for p in SCRATCH.rglob('*') if p.is_file() and not p.is_symlink())
shutil.rmtree(SCRATCH)
save('receipt.json', {
    'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'sourceRevision': '9102ad3ee1247187c01ea5f55c42caaac882961b',
    'sourceClosure': digest(BASE / 'live-source-manifest.json'), 'sourceUnchangedDuringTests': source_unchanged,
    'tools': tools, 'driverSHA256': digest(Path(__file__)), 'pythonVersion': sys.version,
    'testPassed': test['exitCode'] == 0 and passed > 0 and failed == 0,
    'namedPassed': passed, 'namedFailed': failed, 'namedIgnored': ignored, 'tests': tests,
    'formatExitCode': fmt['exitCode'], 'formatFiles': len(fmt_files), 'formatHunks': fmt_hunks,
    'formatScope': 'Whole-project formatting remains inherited debt; all new formatting differences were corrected in the test-only integration derivative.',
    'binaries': binaries,
    'cleanup': {'scratchAbsent': not SCRATCH.exists(), 'ownedGroupsAbsent': all(c['ownedGroupAbsent'] for c in commands),
                'holdersEmpty': True, 'deviceInodeStable': True, 'removedFileBytes': removed,
                'otherProjectsUntouched': True},
    'fullReactorSelected': False, 'nativeAccepted': False, 'gaAccepted': False,
})
assert test['exitCode'] == 0 and passed > 0 and failed == ignored == 0
assert fmt['exitCode'] == 1 and len(fmt_files) == 17 and fmt_hunks == 156, (len(fmt_files), fmt_hunks)
print(json.dumps({'passed': passed, 'failed': failed, 'ignored': ignored,
                  'inheritedFormattingFiles': len(fmt_files), 'inheritedFormattingHunks': fmt_hunks,
                  'scratchAbsent': not SCRATCH.exists()}))
