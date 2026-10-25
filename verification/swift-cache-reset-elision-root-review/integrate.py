#!/usr/bin/env python3
"""Root-selected exact integration and bounded private Swift host controls."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import time

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent.parent
PACKET = ROOT / 'verification/swift-cache-reset-elision'
TOOLS = Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


assert not (OUT / 'receipt.json').exists(), 'Never replay this integration receipt'
assert sha(PACKET / 'seal.json') == 'b62d70cb004eda9d52ebc208fe1c752535cc256a36c8f91c6aae02de5971da51'
verification = subprocess.run(['python3', '-B', str(PACKET / 'verify.py')], cwd=ROOT, capture_output=True)
(OUT / 'packet-verify.stdout').write_bytes(verification.stdout)
(OUT / 'packet-verify.stderr').write_bytes(verification.stderr)
assert verification.returncode == 0, verification.stderr
baseline = json.loads((PACKET / 'baseline-manifest.json').read_text())
candidate = json.loads((PACKET / 'candidate-source-manifest.json').read_text())
assert len(baseline) == len(candidate) == 132
assert {p: sha(ROOT / 'vm' / p) for p in baseline} == baseline
changed = [p for p in baseline if baseline[p] != candidate[p]]
assert changed == ['src/experimental_swift_reactor/cache.rs',
                   'src/experimental_swift_reactor/cache_tests.rs',
                   'src/experimental_swift_reactor/lifecycle_tests.rs']
save('source-review.json', {
    'baselineClosureSHA256': sha(PACKET / 'baseline-manifest.json'),
    'candidateClosureSHA256': sha(PACKET / 'candidate-source-manifest.json'),
    'candidatePatchSHA256': sha(PACKET / 'candidate.patch'),
    'changedFiles': changed,
    'productionReview': 'Remove only redundant clearing loop; preserve arena length and ordinary meter.check() before each pass. Shared decoder, constructor and runtime limits unchanged.',
    'testReview': 'Dirty actual scratch before both passes; expected IR, malformed internal decoder cases, boundary precedence, exhaustive budgets/cancellation and exact lifecycle credit expectations. All new seams cfg(test).',
    'globalFormatting': 'Same 16 inherited failing files; all three candidate files formatted.'})
for relative in changed:
    source = PACKET / 'candidate/vm' / relative
    assert sha(source) == candidate[relative]
    shutil.copyfile(source, ROOT / 'vm' / relative)
assert {p: sha(ROOT / 'vm' / p) for p in candidate} == candidate
save('integrated-manifest.json', candidate)
target = OUT / 'target'
assert not target.exists()
env = {**os.environ, 'CARGO_TARGET_DIR': str(target), 'CARGO_NET_OFFLINE': 'true',
       'CARGO_BUILD_JOBS': '2', 'RUST_TEST_THREADS': '1', 'CARGO_INCREMENTAL': '0'}
env['PATH'] = str(TOOLS) + ':' + env['PATH']
commands = []
accepted = False
try:
    for label, test_filter, expected in [
        ('reset-elision', 'reset_elision_', 4),
        ('lifecycle-sl13', 'swift_lifecycle_sl13_cumulative_instruction_host_and_cache_usage', 1),
        ('lifecycle-sl14', 'swift_lifecycle_sl14_later_work_cache_and_absolute_deadline_do_not_reset', 1),
    ]:
        argv = [str(TOOLS / 'cargo'), 'test', '--locked', '--offline', '--no-default-features',
                '--features', 'experimental-swift-reactor', '--lib', test_filter,
                '--', '--nocapture', '--test-threads=1']
        started = time.monotonic()
        signals = []
        timeout = False
        with (OUT / (label + '.stdout')).open('wb') as stdout, (OUT / (label + '.stderr')).open('wb') as stderr:
            child = subprocess.Popen(argv, cwd=ROOT / 'vm', env=env, stdout=stdout, stderr=stderr, start_new_session=True)
            try:
                code = child.wait(timeout=90)
            except subprocess.TimeoutExpired:
                timeout = True
                for sig in [signal.SIGTERM, signal.SIGKILL]:
                    if child.poll() is not None:
                        break
                    os.killpg(child.pid, sig)
                    signals.append(sig.name)
                    try:
                        child.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        continue
                code = child.poll()
        table = subprocess.run(['/bin/ps', '-axo', 'pid=,ppid=,pgid='], capture_output=True, timeout=5)
        assert table.returncode == 0
        rows = [list(map(int, row.split())) for row in table.stdout.decode().splitlines() if row.strip()]
        assert all(len(row) == 3 for row in rows)
        matching = [row for row in rows if row[2] == child.pid]
        output = (OUT / (label + '.stdout')).read_text()
        found = re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;', output)
        record = dict(argv=argv, cwd=str(ROOT / 'vm'), exitCode=code,
                      elapsedSeconds=time.monotonic()-started, timeoutSeconds=90,
                      timedOut=timeout, pid=child.pid, processGroup=child.pid,
                      processGroupMembers=matching, signalsSent=signals,
                      expectedTests=expected, testResults=found,
                      sourceManifestSHA256=sha(PACKET / 'candidate-source-manifest.json'),
                      stdoutSHA256=sha(OUT / (label + '.stdout')),
                      stderrSHA256=sha(OUT / (label + '.stderr')))
        commands.append(record)
        save(label + '.command.json', record)
        print(json.dumps({'label': label, 'exitCode': code, 'tests': found, 'groupEmpty': not matching}), flush=True)
        assert code == 0 and not timeout and not matching and found == [(str(expected), '0', '0')]
    accepted = True
finally:
    holders = subprocess.run(['/usr/sbin/lsof', '-nP', '+D', str(target)], capture_output=True, timeout=20)
    (OUT / 'holders.stdout').write_bytes(holders.stdout)
    (OUT / 'holders.stderr').write_bytes(holders.stderr)
    clean = holders.returncode == 1 and holders.stdout == holders.stderr == b'' and all(not c['processGroupMembers'] for c in commands)
    if clean and target.exists():
        shutil.rmtree(target)
    final = {p: sha(ROOT / 'vm' / p) for p in candidate}
    tools = {name: {'sha256': sha(TOOLS / name), 'version': subprocess.check_output([str(TOOLS / name), '--version'], text=True).strip()} for name in ['rustc', 'cargo']}
    save('receipt.json', dict(schema=1, observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        status='accepted-live-private-cache-integration' if accepted and clean and final == candidate else 'incomplete',
        baselineRevision='7744c1cc28b24a46f4339b25b38ce4d0cf76cbe8',
        producerSealSHA256=sha(PACKET / 'seal.json'), producerReceiptSHA256=sha(PACKET / 'receipt.json'),
        sourceManifestSHA256=sha(PACKET / 'candidate-source-manifest.json'), sourceFiles=132,
        sourceUnchangedDuringTests=final == candidate, commands=commands, tools=tools,
        ownedTargetRemoved=not target.exists(), holderCheckExitCode=holders.returncode,
        globalFormatting='16 unchanged inherited files; three changed files clean',
        existingIgnoredRegressionTests='8 default / 9 compatibility and all-feature per mode remain ignored',
        fullTargetSelected=False, nativeExecuted=False, gaAccepted=False))
assert accepted and clean and final == candidate
