#!/usr/bin/env python3
"""Finish custody verification after the sole diagnostic attempt; never boot or signal."""
import datetime
import hashlib
import json
import pathlib
import shutil
import socket
import subprocess

OUT = pathlib.Path(__file__).resolve().parent
ROOT = OUT.parents[2]
HELD = {20745, 20770, 20780, 20817, 20842, 20851, 20866, 2424, 2621}


def sha(path):
    with pathlib.Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, data):
    pathlib.Path(path).write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')


r = json.loads((OUT / 'receipt.json').read_text())
groups = []
for entry in r['commands']:
    assert entry['pgid'] not in HELD
    argv = ['pgrep', '-g', str(entry['pgid'])]
    probe = subprocess.run(argv, capture_output=True, text=True, timeout=5)
    groups.append({'name': entry['name'], 'pid': entry['pid'], 'pgid': entry['pgid'],
                   'probe': argv, 'exitCode': probe.returncode, 'members': probe.stdout,
                   'stderr': probe.stderr, 'groupAbsent': probe.returncode == 1})
ports = {}
for port in [5570, 5571, int(r['adbServerPort'])]:
    with socket.socket() as probe:
        try:
            probe.bind(('127.0.0.1', port))
            ports[str(port)] = 'released'
        except OSError as failure:
            ports[str(port)] = str(failure)
lock = json.loads((OUT / 'source-lock.json').read_text())
changed = {rel: {'before': expected, 'after': sha(ROOT / rel)}
           for rel, expected in lock['files'].items() if sha(ROOT / rel) != expected}
scratch = pathlib.Path(r['scratch'])
snapshot_stable = all(sha(scratch / 'inputs' / rel) == expected
                      for rel, expected in lock['files'].items())
save(OUT / 'source-postflight.json', {'changedInputs': changed, 'inputCount': len(lock['files']),
                                     'snapshotStable': snapshot_stable})
baseline = OUT.parent / 'android-runtime'
frozen = json.loads((OUT / 'baseline-manifest.json').read_text())['files']
current = {str(p.relative_to(baseline)): {'sha256': sha(p), 'bytes': p.stat().st_size}
           for p in sorted(baseline.rglob('*')) if p.is_file()}
save(OUT / 'baseline-postflight.json', {'byteForBytePreserved': current == frozen,
                                      'fileCount': len(current),
                                      'changed': sorted(p for p in set(current) | set(frozen)
                                                        if current.get(p) != frozen.get(p))})
r['sourceStable'] = not changed
r['baselineByteForBytePreserved'] = current == frozen
r['status'] = r['runtime']['status']
r['smokePassed'] = r['runtime']['passed']
r['cleanup'].update(groups=groups, ports=ports, allOwnedGroupsClosed=all(g['groupAbsent'] for g in groups),
                    recoveryReceipt='cleanup-recovery.json',
                    runnerFailure='PermissionError in killpg(owned group, 0) after graceful emulator shutdown',
                    runnerExitCode=1,
                    privateKeyRetained=False)
assert scratch.parent == pathlib.Path('/tmp') and scratch.name.startswith('mixer-20261107-android-readiness-')
if r['cleanup']['allOwnedGroupsClosed'] and all(v == 'released' for v in ports.values()):
    shutil.rmtree(scratch)
r['cleanup']['scratchRemoved'] = not scratch.exists()
r['apkRetained'] = False
r['executedRunnerSHA256'] = '3712fd86f33820118fbe3856e079e676557b7c0774d3d3b6151b09252073c4c4'
r['currentRunnerSHA256'] = sha(OUT / 'run_diagnostic.py')
r['runnerPostRunChange'] = 'Cleanup-only: reap before probing and use scoped pgrep after PermissionError. No second build or emulator attempt.'
r['finalizationCommand'] = ['python3', str(pathlib.Path(__file__).resolve())]
r['finishedUTC'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
save(OUT / 'receipt.json', r)
print(json.dumps({k: r[k] for k in ['status', 'sourceStable', 'baselineByteForBytePreserved', 'finishedUTC']}))
print(json.dumps(r['cleanup'], indent=2))
