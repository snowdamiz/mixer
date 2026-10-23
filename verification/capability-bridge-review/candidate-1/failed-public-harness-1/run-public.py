#!/usr/bin/env python3
"""Unmodified public consumer tests against exact candidate1 source and archive."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FREEZE = '318d4ced6ae36e7f88cc80926c0c50a689e9a0ea7812b2a2a7457f7ab8325bd6'
SOURCE = ROOT / 'experimental-capability-runtime/.build/qualification-2026-10-23-candidate-1/source'
MANIFEST = ROOT / 'experimental-capability-runtime/verification/2026-10-23-candidate-1/source-manifest.sha256'
STAGE = ROOT / 'experimental-capability-runtime/build-verification/local/qualified-final-v3/host'
ARCHIVE_SHA = 'a015ff65980422dd0b9c5cad2e28741d1e5ba478e0f657dcaedf75477d553b72'


def sha(data): return hashlib.sha256(data).hexdigest()
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()


def main():
    out = HERE / 'candidate-1'
    out.mkdir(exist_ok=False)
    raw = MANIFEST.read_bytes(); assert sha(raw) == FREEZE
    entries = [row.split('  ', 1) for row in raw.decode().splitlines()]
    archive = STAGE / 'lib/libmixer_vm_capability_experimental.a'
    assert sha(archive.read_bytes()) == ARCHIVE_SHA
    headers = {}
    for name in ['mixer_vm.h', 'mixer_vm_capability.h']:
        content = (STAGE / 'include' / name).read_bytes()
        baseline = subprocess.check_output(['git', 'show', 'b25e3b7de2391a80d12e7fd75e60903495bec120:vm/include/' + name], cwd=ROOT)
        assert content == baseline
        headers[name] = sha(content)
    base = Path(tempfile.mkdtemp(prefix='mixer-independent-bridge-candidate1-'))
    public = base / 'public'
    public.mkdir()
    for digest, relative in entries:
        content = (SOURCE / relative).read_bytes(); assert sha(content) == digest, relative
        target = public / relative; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(content)
    review = public / 'verification/capability-bridge-review'
    review.mkdir(parents=True)
    review_inputs = {}
    for path in [HERE / 'Package.swift', *sorted((HERE / 'PublicHarness').rglob('*'))]:
        if not path.is_file(): continue
        relative = path.relative_to(HERE); content = path.read_bytes()
        target = review / relative; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(content)
        review_inputs[str(relative)] = sha(content)
    (out / 'source-manifest.sha256').write_bytes(raw)
    receipt = {'status': 'running', 'started_at': now(), 'source_manifest_sha256': FREEZE,
               'source_files': len(entries), 'immutable_owner_export': str(SOURCE), 'public_source_copy': str(public),
               'workspace': str(base), 'source_is_uncommitted_candidate_freeze': True,
               'native_revision': 'b25e3b7de2391a80d12e7fd75e60903495bec120',
               'archive': {'path': str(archive.relative_to(ROOT)), 'sha256': ARCHIVE_SHA},
               'headers_sha256': headers, 'review_input_sha256': review_inputs,
               'driver_sha256': sha(Path(__file__).read_bytes()), 'commands': [],
               'scope': 'Unmodified public Swift consumer against exact frozen SDK/bridge source and pinned one native static archive; host only; no internal hooks',
               'no_devices_production_edits_or_push': True}
    def save(): (out / 'public-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    def check():
        for digest, relative in entries:
            assert sha((SOURCE / relative).read_bytes()) == digest, relative
            assert sha((public / relative).read_bytes()) == digest, relative
        assert sha(archive.read_bytes()) == ARCHIVE_SHA
        for name, digest in headers.items(): assert sha((STAGE / 'include' / name).read_bytes()) == digest
    env = dict(os.environ, DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer')
    def run(name, command, scope, timeout=120):
        began = time.monotonic()
        try:
            result = subprocess.run(command, cwd=public, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
            output, code = result.stdout, result.returncode
        except subprocess.TimeoutExpired as error:
            output, code = (error.stdout or b'') + b'\nIndependent review timeout\n', 124
        log = out / (name + '.log'); log.write_bytes(output)
        receipt['commands'].append({'name': name, 'argv': command, 'cwd': str(public), 'environment': {'DEVELOPER_DIR': env['DEVELOPER_DIR']},
                                    'exit_code': code, 'elapsed_seconds': time.monotonic() - began,
                                    'log': str(log.relative_to(ROOT)), 'sha256': sha(output), 'scope': scope})
        save(); check(); print(name + ': ' + str(code), flush=True)
        if code: print(output.decode(errors='replace')[-14000:], flush=True)
        return code
    save()
    for name, command in [('swift-version', ['swift', '--version']), ('host-version', ['uname', '-a']),
                          ('xcode-version', ['xcodebuild', '-version']), ('python-version', ['python3', '--version'])]:
        if run(name, command, 'Observed host review tools'): return 1
    for mode in ['debug', 'release']:
        command = ['swift', 'test', '-v', '--package-path', str(review), '--scratch-path', str(base / 'public-build'),
                   '--configuration', mode, '-Xcc', '-I' + str(STAGE / 'include'),
                   '-Xlinker', '-L' + str(STAGE / 'lib'), '-Xswiftc', '-warnings-as-errors']
        if run('public-' + mode, command, 'Actual independent public API tests, real Wasm and concrete storage; no test hooks'):
            receipt['status'] = 'failed'; receipt['completed_at'] = now(); save(); return 1
    check()
    receipt.update(status='public checks passed; internal/source/owner audit pending', completed_at=now(),
                   immutable_export_and_public_copy_unchanged=True, native_archive_and_headers_unchanged=True)
    save()
    print(json.dumps({'public_checks_passed': True, 'workspace': str(base), 'final_review': False}), flush=True)
    return 0


if __name__ == '__main__': raise SystemExit(main())
