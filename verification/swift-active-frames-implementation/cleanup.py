#!/usr/bin/env python3
"""Retire only this lane's disposable host build scratch after evidence retention.

No native tools or process-wide kill commands are used. Refuse cleanup if any
process has an open file or command path under this lane's build directory.
"""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
BUILD = HERE / 'build'
OUT = HERE / 'process-cleanup'
OUT.mkdir(exist_ok=True)


def sha(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def save(name, value):
    (OUT / name).write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')


def observations(label):
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    ps = subprocess.run(['ps', '-axo', 'pid=,ppid=,command='], capture_output=True, text=True)
    assert ps.returncode == 0
    matching = []
    for line in ps.stdout.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) == 3 and str(BUILD) + '/' in parts[2] and int(parts[0]) not in [os.getpid(), os.getppid()]:
            matching.append(line)
    (OUT / (label + '-matching-processes.stdout')).write_text('\n'.join(matching) + ('\n' if matching else ''))
    lsof_args = ['lsof', '-nP', '+D', str(BUILD), '-Fpcn']
    if BUILD.exists():
        lsof = subprocess.run(lsof_args, capture_output=True, text=True)
        assert lsof.returncode in [0, 1], lsof.stderr
        (OUT / (label + '-lsof.stdout')).write_text(lsof.stdout)
        (OUT / (label + '-lsof.stderr')).write_text(lsof.stderr)
        assert not lsof.stdout and not matching, (matching, lsof.stdout)
        code = lsof.returncode
    else:
        code = None
    return dict(observedUTC=started, psArgv=['ps', '-axo', 'pid=,ppid=,command='],
                matchingOwnedBuildProcesses=matching, lsofArgv=lsof_args,
                lsofExitCode=code, lsofSkippedBecauseBuildAbsent=not BUILD.exists())


before = observations('before')
assert BUILD.exists() and BUILD.resolve().parent == HERE.resolve()
# Retain the current source bytes and executables from the small early manual
# scratch roots as historical capture only. No source digest is backdated to
# a mutable early command. Final qualifying executables already have complete
# independent portable archives in their immutable result/metadata packets.
members = []
with tarfile.open(OUT / 'historical-manual-scratch.tar.gz', 'w:gz') as archive:
    for name in ['first-runtime', 'accounting-layout']:
        path = BUILD / name
        if not path.exists():
            continue
        for item in sorted(path.rglob('*')):
            if item.is_file():
                member = str(item.relative_to(BUILD))
                archive.add(item, arcname=member, recursive=False)
                members.append(dict(member=member, sha256=sha(item)))
    for name in ['first-runtime-target', 'initial-target', 'typed-unit', 'accounting-layout-target']:
        for item in sorted((BUILD / name).glob('**/deps/mixer_vm-*')):
            if item.is_file() and item.suffix == '' and os.access(item, os.X_OK):
                member = str(item.relative_to(BUILD))
                archive.add(item, arcname=member, recursive=False)
                members.append(dict(member=member, sha256=sha(item)))
save('historical-manual-scratch.json', dict(
    scope='Capture at cleanup time only; not a contemporaneous source binding or final qualification.',
    archive='historical-manual-scratch.tar.gz', archiveSHA256=sha(OUT / 'historical-manual-scratch.tar.gz'),
    members=members))
size = subprocess.run(['du', '-sk', str(BUILD)], capture_output=True, text=True, check=True)
(OUT / 'before-size.stdout').write_text(size.stdout)
# Recheck immediately before this narrow removal, after capture has closed all
# files. Every source archive, log, failed attempt and final binary is outside
# BUILD; this is the only tree removed.
pre_remove = observations('immediately-before-remove')
shutil.rmtree(BUILD)
after = observations('after')
save('receipt.json', dict(
    status='owned-host-build-scratch-removed-no-owned-build-processes',
    before=before, immediatelyBeforeRemoval=pre_remove, after=after,
    removedPath=str(BUILD), removedReportedKiB=int(size.stdout.split()[0]),
    buildDirectoryAbsent=not BUILD.exists(), processesStopped=[],
    processStopReason='All owned Cargo/test/compiler commands had already exited; no process needed termination.',
    preserved='All immutable source/result/metadata archives, raw logs, receipts, compact qualifying binaries and historical manual capture remain outside removed build/.',
    computerUse=False, nativeDiscovery=False, nativeBootInstallRun=False,
    otherProjectsTouched=False))
print(OUT / 'receipt.json')
