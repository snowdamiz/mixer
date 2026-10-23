#!/usr/bin/env python3
"""Run labelled derived candidate1 probes; never edit production source."""
import datetime
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / 'candidate-1'


def sha(raw): return hashlib.sha256(raw).hexdigest()
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt', type=int, default=1)
    parser.add_argument('--only', choices=['late-close'])
    args = parser.parse_args()
    assert args.attempt >= 1
    logs = OUT if args.attempt == 1 else OUT / ('internal-replay-' + str(args.attempt))
    if args.attempt > 1: logs.mkdir(exist_ok=False)
    public = json.loads((OUT / 'public-replay-2/public-receipt.json').read_text())
    assert public['status'].startswith('public checks passed')
    base = Path(public['workspace'])
    derived = base / 'derived'
    mapping_bytes = (derived / 'derived-review.json').read_bytes()
    mapping = json.loads(mapping_bytes)
    assert mapping['input_manifest_sha256'] == public['source_manifest_sha256']
    (logs / 'derived-map.json').write_bytes(mapping_bytes)
    source = Path(public['immutable_owner_export'])
    stage = ROOT / 'experimental-capability-runtime/build-verification/local/qualified-final-v3/host'
    archive = ROOT / public['archive']['path']
    def check():
        for row in mapping['input_files']:
            assert sha((source / row['path']).read_bytes()) == row['input_sha256'], row['path']
            expected = mapping['derived_source_sha256'].get(row['path'], row['input_sha256'])
            assert sha((derived / row['path']).read_bytes()) == expected, row['path']
        for relative, digest in mapping['derived_source_sha256'].items():
            assert sha((derived / relative).read_bytes()) == digest, relative
        review = derived / 'verification/capability-bridge-review'
        for relative, digest in mapping['review_input_sha256'].items():
            path = (review / 'InternalHarness/Tests/Fixtures' / Path(relative).name if relative.startswith('fixtures/') else review / relative)
            assert sha(path.read_bytes()) == digest, relative
        assert sha(archive.read_bytes()) == public['archive']['sha256']
        for name, digest in public['headers_sha256'].items(): assert sha((stage / 'include' / name).read_bytes()) == digest
    check()
    receipt = {'status': 'running', 'started_at': now(), 'source_manifest_sha256': public['source_manifest_sha256'],
               'derived_map_sha256': sha(mapping_bytes), 'archive': public['archive'], 'headers_sha256': public['headers_sha256'],
               'driver_sha256': sha(Path(__file__).read_bytes()), 'commands': [],
               'scope': 'Labelled review-only scheduling/local-metadata copies; real installed storage is retained; never substitute for unmodified public results',
               'sanitizer_scope': 'Swift and built C shim instrumentation with unchanged uninstrumented pinned Rust static archive; no whole-stack race-freedom claim',
               'fault_filters_are_separate_processes': True, 'production_edits_or_devices': False}
    target = logs / 'internal-receipt.json'
    if target.exists(): raise RuntimeError('preserve previous receipt before an explicit replay')
    def save(): target.write_text(json.dumps(receipt, indent=2) + '\n')
    env = dict(os.environ, DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer')
    def run(name, command, scope, timeout=180):
        started = time.monotonic()
        try:
            result = subprocess.run(command, cwd=derived, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
            output, code = result.stdout, result.returncode
        except subprocess.TimeoutExpired as error:
            output, code = (error.stdout or b'') + b'\nIndependent review timeout\n', 124
        log = logs / (name + '.log'); log.write_bytes(output)
        receipt['commands'].append({'name': name, 'argv': command, 'cwd': str(derived), 'environment': {'DEVELOPER_DIR': env['DEVELOPER_DIR']},
                                    'exit_code': code, 'elapsed_seconds': time.monotonic() - started,
                                    'log': str(log.relative_to(ROOT)), 'sha256': sha(output), 'scope': scope})
        save(); check(); print(name + ': ' + str(code), flush=True)
        if code: print(output.decode(errors='replace')[-16000:], flush=True)
        return code
    def command(package, scratch, mode, pattern, tsan=False):
        return ['swift', 'test', '-v', '--package-path', str(package), '--scratch-path', str(scratch), '--configuration', mode,
                '-Xcc', '-I' + str(stage / 'include'), '-Xlinker', '-L' + str(stage / 'lib'),
                '-Xswiftc', '-warnings-as-errors', '--filter', pattern] + (['--sanitize', 'thread'] if tsan else [])
    package = derived / 'verification/capability-bridge-review/InternalHarness'
    save()
    if args.only == 'late-close':
        code = run('late-close-debug', command(package, base / 'internal-build', 'debug',
                   'InternalBridgeReviewTests.testTakeReturningAfterCloseRegistersOnlyLocalNoIOExit'),
                   'Focused root-requested normal-close status probe; derived C-take scheduling gate, no production edit')
        receipt.update(status='focused late-close probe passed' if code == 0 else 'focused late-close probe failed', completed_at=now())
        save(); return 1 if code else 0
    for mode in ['debug', 'release']:
        for label, pattern in [('ordering', 'InternalBridgeReviewTests'), ('metadata-fault', 'InternalBridgeMetadataFaultReviewTests'),
                               ('constructor-fault', 'InternalBridgeConstructorFaultReviewTests')]:
            if run(label + '-' + mode, command(package, base / 'internal-build', mode, pattern),
                   'Review-derived ' + label + '; isolated test process; exact mutation map recorded'):
                receipt.update(status='failed', completed_at=now()); save(); return 1
    original = Path(public['public_source_copy']) / 'verification/capability-bridge-review'
    if run('public-tsan', command(original, base / 'public-build', 'debug', 'PublicBridgeReviewTests', True),
           'Unmodified public consumer under Swift/C shim TSan; pinned Rust archive not instrumented'):
        receipt.update(status='failed', completed_at=now()); save(); return 1
    if run('ordering-tsan', command(package, base / 'internal-build', 'debug', 'InternalBridgeReviewTests', True),
           'Labelled derived ordering/retention under Swift/C shim TSan; pinned Rust archive not instrumented'):
        receipt.update(status='failed', completed_at=now()); save(); return 1
    receipt.update(status='internal checks passed; final source/owner receipt audit pending', completed_at=now(),
                   source_export_derived_copy_and_native_artifacts_unchanged=True)
    save(); print(json.dumps({'passed': True, 'final_review': False}))
    return 0


if __name__ == '__main__': raise SystemExit(main())
