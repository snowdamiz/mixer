"""Ordinary trusted-host offline reconciliation; no runtime admission claim.

The caller supplies this source packet's externally recorded seal digest. The
seal pins the launcher/manifest; the manifest pins descendant utility/data files.
No checksum cycle or self-approval status is used.
"""
from pathlib import Path
import argparse
import contextlib
import datetime
import hashlib
import json
import os
import platform
import runpy
import signal
import subprocess
import sys
import time

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[3]
MANIFEST_SHA256 = 'deef4efeae2adf4d358036f31e60c8802bba1135128ca1a72622ed1f38bdfd93'


def ident(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def verify(expected_seal):
    assert ident(BASE / 'seal.json')['sha256'] == expected_seal, 'externally recorded source seal'
    seal = json.loads((BASE / 'seal.json').read_bytes())
    assert {str(p.relative_to(BASE)) for p in BASE.rglob('*') if p.is_file()} == {'seal.json'} | {item['path'] for item in seal['members']}
    for item in seal['members']:
        assert ident(BASE / item['path']) == {key: item[key] for key in ('bytes', 'sha256')}
    assert ident(BASE / 'input-manifest.json')['sha256'] == MANIFEST_SHA256
    manifest = json.loads((BASE / 'input-manifest.json').read_bytes())
    for root in manifest['closed_roots']:
        base = REPO / root['root']
        paths = list(base.rglob('*'))
        assert not any(path.is_symlink() for path in paths)
        assert {str(path.relative_to(REPO)) for path in paths if path.is_file()} == set(root['paths'])
    for item in manifest['files']:
        relative = Path(item['path'])
        assert not relative.is_absolute() and '..' not in relative.parts
        assert ident(REPO / relative) == {key: item[key] for key in ('bytes', 'sha256')}
    return manifest


class Tee:
    def __init__(self, saved, visible):
        self.saved, self.visible = saved, visible

    def write(self, value):
        self.saved.write(value)
        self.visible.write(value)
        return len(value)

    def flush(self):
        self.saved.flush()
        self.visible.flush()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-seal-sha256', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    out = args.output.resolve()
    assert not out.exists() and out.is_relative_to(BASE.parent) and not out.is_relative_to(BASE)
    out.mkdir()
    commands = []
    status = 'failed'
    closure_entry = closure_exit = False
    started = time.monotonic()
    manifest = None
    try:
        signal.alarm(60)
        manifest = verify(args.source_seal_sha256)
        closure_entry = True
        signal.alarm(0)
        parent, recovery = REPO / manifest['data_parent'], REPO / manifest['recovery']
        argv = [sys.executable, '-B', str(BASE / 'code/test_observation_auditor_v2.py'), '--run', str(parent),
                '--recovery', str(recovery), '--output', str(out / 'fresh-controls.json')]
        env = {'PATH': '/usr/bin:/bin', 'LANG': 'en_US.UTF-8', 'LC_ALL': 'en_US.UTF-8', 'TZ': 'UTC'}
        with (out / 'controls.stdout').open('wb') as stdout, (out / 'controls.stderr').open('wb') as stderr:
            child = subprocess.Popen(argv, cwd=REPO, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
            timed = False
            child_start = time.monotonic()
            try:
                child.wait(timeout=60)
            except subprocess.TimeoutExpired:
                timed = True
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
            except BaseException:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
                raise
        commands.append({'argv': argv, 'exit': child.returncode, 'timeout': timed, 'maximum_seconds': 60,
                         'elapsed_seconds': time.monotonic() - child_start, 'reaped': True,
                         'stdout': ident(out / 'controls.stdout'), 'stderr': ident(out / 'controls.stderr')})
        assert child.returncode == 0 and not timed, 'fresh retained29 and final controls'
        signal.alarm(60)
        verify(args.source_seal_sha256)
        signal.alarm(0)
        sys.path.insert(0, str(BASE / 'code'))
        sys.argv = [str(BASE / 'code/audit_selected_replay_v2.py'), '--run', str(parent), '--recovery', str(recovery),
                    '--require-historical-states', '--output', str(out / 'complete-proved-unresolved-ledger.json')]
        with (out / 'audit.stdout').open('w') as saved_stdout, (out / 'audit.stderr').open('w') as saved_stderr:
            with contextlib.redirect_stdout(Tee(saved_stdout, sys.stdout)), contextlib.redirect_stderr(Tee(saved_stderr, sys.stderr)):
                runpy.run_path(str(BASE / 'code/audit_selected_replay_v2.py'), run_name='__main__')
        status = 'reconciled-immutable-source-data-closure; not-qualified'
    finally:
        signal.alarm(60)
        try:
            verify(args.source_seal_sha256)
            closure_exit = True
        finally:
            signal.alarm(0)
            save(out / 'receipt.json', {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 'status': status, 'source_packet_seal_sha256': args.source_seal_sha256, 'manifest_sha256': MANIFEST_SHA256,
                 'utility_data_closure_entry_verified': closure_entry, 'utility_data_closure_exit_verified': closure_exit,
                 'commands': commands, 'all_owned_children_reaped': all(item['reaped'] for item in commands),
                 'python': sys.version, 'python_executable': sys.executable, 'platform': platform.platform(),
                 'elapsed_seconds': time.monotonic() - started,
                 'bounds': 'Closure checks and each control child <=60s; offline parent audits a closed finite file roster with <=60s per raw/compact file.',
                 'trusted_runtime_boundary': 'Ordinary caller-selected local Python/OS. No interpreter startup/closure, v5 correction, full execution admission, native, OTA or GA claim.',
                 'qualified': False})


if __name__ == '__main__':
    main()
