#!/usr/bin/env python3
"""Exercise the selected isolated closure without changing live VM bytes."""
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
ROOT = OUT.parents[1]
SOURCE = OUT / 'source'
TARGET = OUT / 'owned-target'
TOOLS = Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

manifest = json.loads((OUT / 'source-manifest.json').read_bytes())
baseline = json.loads((OUT / 'baseline-manifest.json').read_bytes())
assert not (OUT / 'receipt-v3.json').exists() and not TARGET.exists()
assert {n: sha(SOURCE / n) for n in manifest} == manifest
assert {n: sha(ROOT / 'vm' / n) for n in baseline} == baseline
env = {**os.environ, 'PATH': str(TOOLS) + ':' + os.environ['PATH'],
       'CARGO_TARGET_DIR': str(TARGET), 'CARGO_NET_OFFLINE': 'true',
       'CARGO_BUILD_JOBS': '2', 'CARGO_INCREMENTAL': '0', 'RUST_TEST_THREADS': '1'}
first_receipt = json.loads((OUT / 'receipt-v2.json').read_bytes())
assert first_receipt['commands'][0]['exitCode'] == 0 and first_receipt['commands'][0]['testResults'] == [['404', '0', '0']]
commands = first_receipt['commands'][:3]
assert [c['testResults'] for c in commands] == [[['404','0','0']],[['29','0','0']],[['21','0','0']]]
passed = False
specs = [
    ('lifecycle-debug-corrected', ['test', '--no-default-features', '--features', 'experimental-swift-reactor', '--lib', 'experimental_swift_reactor::lifecycle::tests::', '--', '--test-threads=1'], 49, 0),
    ('frozen-trace', ['test', '--no-default-features', '--features', 'experimental-function-cache', '--lib', 'frozen_layout_and_trace_observation', '--', '--nocapture', '--test-threads=1'], 1, 0),
    ('clippy', ['clippy', '--no-default-features', '--features', 'experimental-swift-reactor', '--lib', '--', '-D', 'warnings'], None, None),
]
try:
    for label, args, expected, ignored in specs:
        argv = [str(TOOLS / 'cargo'), args[0], '--locked', '--offline', *args[1:]]
        start = time.monotonic(); sent = []; timed_out = False
        with (OUT / (label + '.stdout')).open('wb') as stdout, (OUT / (label + '.stderr')).open('wb') as stderr:
            child = subprocess.Popen(argv, cwd=SOURCE, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
            try:
                code = child.wait(timeout=240)
            except subprocess.TimeoutExpired:
                timed_out = True
                for sig in (signal.SIGTERM, signal.SIGKILL):
                    if child.poll() is not None:
                        break
                    os.killpg(child.pid, sig); sent.append(sig.name)
                    try:
                        child.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        pass
                code = child.poll()
        table = subprocess.run(['/bin/ps', '-axo', 'pid=,ppid=,pgid='], capture_output=True, timeout=5)
        assert table.returncode == 0
        members = [list(map(int, s.split())) for s in table.stdout.decode().splitlines() if s.strip()]
        assert all(len(row) == 3 for row in members)
        members = [row for row in members if row[2] == child.pid]
        output = (OUT / (label + '.stdout')).read_text()
        results = re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;', output)
        binaries = []
        for name in re.findall(r'Running .*?\(([^)]+)\)', (OUT / (label + '.stderr')).read_text()):
            path = Path(name)
            if not path.is_absolute():path = SOURCE / path
            if path.is_file():binaries.append({'path': str(path), 'sha256': sha(path), 'bytes': path.stat().st_size})
        record = dict(label=label, argv=argv, cwd=str(SOURCE), exitCode=code,
                      elapsedSeconds=time.monotonic()-start, timeoutSeconds=240, timedOut=timed_out,
                      pid=child.pid, processGroup=child.pid, processGroupMembers=members, signalsSent=sent,
                      stdoutEOF=True, stderrEOF=True, expectedTests=expected, inheritedIgnored=ignored,
                      testResults=results, executedBinaries=binaries,
                      sourceManifestSHA256=sha(OUT / 'source-manifest.json'),
                      stdoutSHA256=sha(OUT / (label+'.stdout')), stderrSHA256=sha(OUT / (label+'.stderr')))
        commands.append(record);save(label+'.command.json',record)
        print(json.dumps({'label':label,'exitCode':code,'tests':results,'groupEmpty':not members}),flush=True)
        assert code == 0 and not timed_out and not members
        if expected is not None:
            assert results == [(str(expected),'0',str(ignored))] and binaries
    passed = True
finally:
    holders = subprocess.run(['/usr/sbin/lsof','-nP','+D',str(TARGET)],capture_output=True,timeout=30)
    (OUT/'holders.stdout').write_bytes(holders.stdout);(OUT/'holders.stderr').write_bytes(holders.stderr)
    clean = holders.returncode == 1 and holders.stdout == holders.stderr == b'' and all(not c['processGroupMembers'] for c in commands)
    removed_bytes = 0
    if clean and TARGET.exists():
        removed_bytes = sum(p.stat().st_size for p in TARGET.rglob('*') if p.is_file() and not p.is_symlink())
        shutil.rmtree(TARGET)
    current = {n:sha(SOURCE/n) for n in manifest}
    live = {n:sha(ROOT/'vm'/n) for n in baseline}
    tool_versions = {n:{'sha256':sha(TOOLS/n),'version':subprocess.check_output([str(TOOLS/n),'--version'],text=True).strip()} for n in ['cargo','rustc']}
    save('receipt-v3.json',dict(schema=1,observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        status='isolated-tests-passed-awaiting-independent-review' if passed and clean and current==manifest and live==baseline else 'incomplete',
        sourceManifestSHA256=sha(OUT/'source-manifest.json'),selectionSHA256=sha(OUT/'selection.json'),
        commands=commands,tools=tool_versions,sourceUnchanged=current==manifest,liveUnchanged=live==baseline,
        ownedTargetRemoved=not TARGET.exists(),removedLogicalBytes=removed_bytes,holderExitCode=holders.returncode,
        liveIntegrated=False,fullTargetExecuted=False,nativeExecuted=False,gaAccepted=False))
assert passed and clean and current==manifest and live==baseline
