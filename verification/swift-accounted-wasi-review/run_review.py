#!/usr/bin/env python3
"""Run original independent review probes on a pinned, review-owned VM copy."""
import datetime
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = pathlib.Path(__file__).resolve().parent
RUST = pathlib.Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
LABEL = sys.argv[1]
SNAPSHOT = BASE / '.build' / LABEL
PROBED = BASE / '.build' / (LABEL + '-probed')
OUT = BASE / LABEL
OUT.mkdir(parents=True, exist_ok=False)
COMMANDS = []
ENV = dict(os.environ, PATH=str(RUST) + ':' + os.environ.get('PATH', ''),
           CARGO_TARGET_DIR=str(BASE / '.build' / (LABEL + '-target')),
           RUSTFLAGS='--check-cfg=cfg(review_borrow_use) --check-cfg=cfg(review_borrow_drop)')


def digest(path):
    data = path.read_bytes()
    try:
        name = str(path.relative_to(ROOT))
    except ValueError:
        name = str(path)
    return dict(path=name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def manifest(source):
    entries = []
    for p in sorted((source / 'vm').rglob('*')):
        if p.is_file():
            info = digest(p)
            info['path'] = str(p.relative_to(source))
            entries.append(info)
    return dict(files=entries, tree_sha256=hashlib.sha256(json.dumps(entries, sort_keys=True, separators=(',', ':')).encode()).hexdigest())


def run(label, args, cwd=PROBED, expected=0, diagnostic=None, env=None):
    started = time.monotonic()
    result = subprocess.run(list(map(str, args)), cwd=cwd, env=env or ENV, capture_output=True, timeout=60)
    stdout = OUT / (label + '.stdout')
    stderr = OUT / (label + '.stderr')
    stdout.write_bytes(result.stdout)
    stderr.write_bytes(result.stderr)
    passed = result.returncode == expected if expected is not None else result.returncode != 0
    if diagnostic:
        passed = passed and diagnostic.encode() in result.stderr
    entry = dict(label=label, argv=list(map(str, args)), cwd=str(cwd), exit_code=result.returncode,
                 expected_exit_code=expected, expected_stderr=diagnostic, expectation_met=passed,
                 elapsed_seconds=time.monotonic() - started, stdout=digest(stdout), stderr=digest(stderr))
    COMMANDS.append(entry)
    print(json.dumps(dict(label=label, exit_code=result.returncode, expectation_met=passed)), flush=True)
    (OUT / 'commands-in-progress.json').write_text(json.dumps(COMMANDS, indent=2) + '\n')
    return result


before = manifest(SNAPSHOT)
(OUT / 'snapshot-before.json').write_text(json.dumps(before, indent=2) + '\n')
shutil.copytree(SNAPSHOT, PROBED)
accounted = PROBED / 'vm/src/experimental_wasi/accounted.rs'
accounted.write_bytes(accounted.read_bytes() + b'\n#[cfg(test)]\n#[path = "review_probes.rs"]\nmod independent_review;\n')
shutil.copy2(BASE / 'independent_probes.rs', PROBED / 'vm/src/experimental_wasi/review_probes.rs')
tests = PROBED / 'vm/src/experimental_wasi/tests.rs'
tests.write_bytes(tests.read_bytes() + b'''
// Review-only access to the existing original check counter; no dispatch code changes.
pub(crate) mod review_hooks {
    use super::*;
    pub(crate) fn checks(context: &WasiContext) -> usize { context.test.checks.get() }
    pub(crate) fn cancel_at(context: &WasiContext, ordinal: usize) { context.test.cancel_at.set(Some(ordinal)); }
}
''')
overlay = manifest(PROBED)
(OUT / 'probe-overlay.json').write_text(json.dumps(overlay, indent=2) + '\n')
run('rustc-version', [RUST / 'rustc', '--version', '--verbose'])
run('cargo-version', [RUST / 'cargo', '--version'])
run('python-version', [sys.executable, '--version'])

for mode in ['debug', 'release']:
    release = ['--release'] if mode == 'release' else []
    run(mode + '-independent-positive', [RUST / 'cargo', 'test', '--offline', '--manifest-path', 'vm/Cargo.toml',
        '--features', 'experimental-swift-reactor', '--lib', *release,
        'independent_review::review_', '--', '--nocapture', '--skip',
        'review_cleanup_first_foreign_control_captures_actual_wasi_observation'])
    expected = 101 if LABEL == 'original' else 0
    run(mode + '-cleanup-first-regression', [RUST / 'cargo', 'test', '--offline', '--manifest-path', 'vm/Cargo.toml',
        '--features', 'experimental-swift-reactor', '--lib', *release,
        'independent_review::review_cleanup_first_foreign_control_captures_actual_wasi_observation', '--', '--nocapture'], expected=expected)

for flag, error in [('review_borrow_use', 'E0502'), ('review_borrow_drop', 'E0505')]:
    run(flag, [RUST / 'rustc', '--edition', '2021', '--crate-name', 'mixer_vm', '--test',
        '--cfg', 'feature="experimental-swift-reactor"', '--cfg', 'feature="experimental-stream-validation"',
        '--cfg', 'feature="experimental-swift-wasi"', '--cfg', flag,
        '--check-cfg', 'cfg(review_borrow_use)', '--check-cfg', 'cfg(review_borrow_drop)',
        'vm/src/lib.rs', '-o', OUT / flag], expected=None, diagnostic=error)

run('public-library', [RUST / 'cargo', 'build', '--offline', '--manifest-path', 'vm/Cargo.toml',
    '--features', 'experimental-swift-reactor', '--lib'])
external = OUT / 'external'
external.mkdir()
snippets = {
    'private-owner': ('use mixer_vm::experimental_wasi::accounted::AccountedWasi; fn main() {}', 'E0603'),
    'private-phase': ('use mixer_vm::experimental_wasi::accounted::WasiConstructionPhase; fn main() {}', 'E0603'),
    'private-control': ('use mixer_vm::experimental_swift_reactor::control::RuntimeControl; fn main() {}', 'E0603'),
    'private-reservation': ('use mixer_vm::experimental_swift_reactor::control::ReservationTicket; fn main() {}', 'E0603'),
    'private-header-helper': ('fn main() { let _ = mixer_vm::experimental_wasi::accounted::accounted_header_bytes(); }', 'E0603'),
    'standalone-no-accounted-constructor': ('fn main() { let _ = mixer_vm::experimental_wasi::WasiContext::new_accounted; }', 'E0599'),
    'standalone-no-deadline-escape': ('fn main() { let c = mixer_vm::experimental_wasi::WasiContext::new(Default::default(), Default::default(), Default::default()).unwrap(); let _ = c.deadline; }', 'E0616'),
}
for label, (code, diagnostic) in snippets.items():
    source = external / (label + '.rs')
    source.write_text(code + '\n')
    run('external-' + label, [RUST / 'rustc', '--edition', '2021', source,
        '--extern', 'mixer_vm=' + str(pathlib.Path(ENV['CARGO_TARGET_DIR']) / 'debug/libmixer_vm.rlib'),
        '-L', 'dependency=' + str(pathlib.Path(ENV['CARGO_TARGET_DIR']) / 'debug/deps'),
        '-o', external / label], expected=None, diagnostic=diagnostic)

after = manifest(SNAPSHOT)
overlay_after = manifest(PROBED)
source_stable = before == after and overlay == overlay_after
receipt = dict(observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
               scope='Independent bounded native review probes; original full ABI proof validated and consumed; no reactor instantiation or guest execution.',
               snapshot=str(SNAPSHOT), snapshot_manifest=digest(OUT / 'snapshot-before.json'),
               source_stable=source_stable, overlay_manifest=digest(OUT / 'probe-overlay.json'),
               probe=digest(PROBED / 'vm/src/experimental_wasi/review_probes.rs'),
               collector=digest(pathlib.Path(__file__)), commands=COMMANDS,
               toolchain_files=[digest(RUST / name) for name in ['rustc', 'cargo']],
               expectations_met=source_stable and all(c['expectation_met'] for c in COMMANDS),
               original_bug_expected=LABEL == 'original', limitations=[
                   'Review snapshot test-only additions expose the existing cancellation check ordinal and inject the independently authored module; product algorithms are unchanged.',
                   'No actual 53 MB reactor allocation, initialization, invocation or corpus qualification.',
                   'No physical phones, mobile qualification, signing, store, publication, separate-repository consumption or GA acceptance.',
                   'Logical capacity and conservative named Rust object reservation observations exclude allocator overhead, RSS and compiler stack measurement.',
                   'Cancellation/deadline remain cooperative; no individual platform/allocator call is preempted.'
               ])
(OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(dict(receipt=str(OUT / 'receipt.json'), expectations_met=receipt['expectations_met'])), flush=True)
sys.exit(0 if receipt['expectations_met'] else 1)
