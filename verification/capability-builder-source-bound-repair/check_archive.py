#!/usr/bin/env python3
"""Rebuild the unchanged pinned VM source, then exercise its three C consumers."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
REVISION = 'fb531a185b7b020fe3e17d6e24d78a0977352c8d'
records = []
scratch = Path(tempfile.mkdtemp(prefix='mixer-capability-source-bound-')).resolve()
artifact = scratch / 'artifact'
result = {'schema': 1, 'sourceRevision': REVISION, 'scratch': str(scratch),
          'scope': 'macOS frozen-source archive build and three C consumer regressions; no native/GA qualification',
          'builderSHA256': hashlib.sha256((ROOT / 'experimental-capability-runtime/build-vm.py').read_bytes()).hexdigest(),
          'runtimeBudgetChanges': False, 'passed': False, 'cleanupPassed': False}


def run(label, command, timeout=180):
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=timeout)
        out, err, code = completed.stdout, completed.stderr, completed.returncode
    except subprocess.TimeoutExpired as error:
        out, err, code = error.stdout or b'', error.stderr or b'', None
    for suffix, data in [('stdout', out), ('stderr', err)]:
        (HERE / f'{label}.{suffix}').write_bytes(data)
    records.append({'label': label, 'command': command, 'cwd': str(ROOT), 'startedUTC': started,
                    'endedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'exitCode': code,
                    'stdoutSHA256': hashlib.sha256(out).hexdigest(), 'stderrSHA256': hashlib.sha256(err).hexdigest()})
    (HERE / 'archive-commands.json').write_text(json.dumps(records, indent=2) + '\n')
    if code != 0:
        raise RuntimeError(f'{label} failed: {code}')
    return out.decode().strip()


try:
    run('archive-build', [sys.executable, '-B', str(ROOT / 'experimental-capability-runtime/build-vm.py'),
                         '--revision', REVISION, '--target', 'host', '--output', str(artifact),
                         '--rustc', '/opt/homebrew/opt/rustup/bin/rustc'])
    receipt = json.loads((artifact / 'receipt.json').read_text())
    assert receipt['source_revision'] == REVISION and receipt['builder_sha256'] == result['builderSHA256']
    assert receipt['source_file_count'] == 139 and len(receipt['public_C_symbols']) == 28
    for name in ['receipt.json', 'source-manifest.sha256'] + [row['log'] for row in receipt['commands']]:
        shutil.copyfile(artifact / name, HERE / ('build-' + name))
    clang = run('clang-path', ['xcrun', '--sdk', 'macosx', '--find', 'clang'])
    sdk = run('sdk-path', ['xcrun', '--sdk', 'macosx', '--show-sdk-path'])
    for label, source in [('smoke', artifact / 'source/vm/tests/capability_ffi_smoke.c'),
                          ('registry', ROOT / 'experimental-capability-runtime/build-tests/mixed_registry.c'),
                          ('guest-ui', ROOT / 'experimental-capability-runtime/build-tests/guest_ui.c')]:
        output = scratch / label
        run(label + '-compile', [clang, '-isysroot', sdk, '-std=c11', '-Wall', '-Wextra', '-Werror',
                                '-mmacosx-version-min=14.0', '-I' + str(artifact / 'include'), str(source),
                                str(artifact / 'lib/libmixer_vm_capability_experimental.a'),
                                '-lpthread', '-ldl', '-lm', '-o', str(output)])
        run(label + '-execute', [str(output)], timeout=30)
    result['passed'] = True
    result['archiveSHA256'] = receipt['library']['sha256']
    result['publicCSymbolCount'] = len(receipt['public_C_symbols'])
finally:
    # The builder owns and verifies each child command group. Do not remove
    # a scratch tree still held by a process after any unsuccessful run.
    scan = subprocess.run(['/usr/sbin/lsof', '-nP', '+D', str(scratch)], capture_output=True, timeout=30)
    (HERE / 'cleanup-lsof.stdout').write_bytes(scan.stdout)
    (HERE / 'cleanup-lsof.stderr').write_bytes(scan.stderr)
    result['holderCheckExitCode'] = scan.returncode
    result['scratchBytes'] = sum(p.stat().st_size for p in scratch.rglob('*') if p.is_file() and not p.is_symlink())
    if scan.returncode == 1 and not scan.stdout and not scan.stderr:
        shutil.rmtree(scratch)
        result['cleanupPassed'] = not scratch.exists()
    result['recordedUTC'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result['bindings'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.iterdir()
                          if p.is_file() and p.name != 'archive-review.json'}
    (HERE / 'archive-review.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['passed', 'cleanupPassed', 'scratchBytes']}), flush=True)
    if not result['cleanupPassed']:
        raise RuntimeError('Owned scratch cleanup could not be established')
