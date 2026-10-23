#!/usr/bin/env python3
"""Independent host review against a Git-object snapshot, never the worktree VM."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
REVISION = '4e37b357ae029d9cdf5e5c6b4281d82f61b65f3a'
EXPECTED = '369b698053b2ca5217819679b9050e0a43a9947c9de87c0b66be4e1722ccbe49'
SCRATCH = ROOT / '.build/capability-mailbox-independent-4e37b35'
SOURCE = SCRATCH / 'source'
HARNESS = SCRATCH / 'harness'
ENV = dict(os.environ)
ENV['PATH'] = '/opt/homebrew/opt/rustup/bin:' + ENV['PATH']
ENV['CARGO_TARGET_DIR'] = str(SCRATCH / 'target')
RECEIPT_PATH = OUT / 'receipt.json'
receipt = {
    'schema': 1,
    'scope': 'Independent Rust-only experimental mailbox code review and adversarial host verification; immutable Git-object export; no production integration or device qualification',
    'reviewed_revision': REVISION,
    'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'environment': {'PATH_prefix': '/opt/homebrew/opt/rustup/bin', 'CARGO_TARGET_DIR': ENV['CARGO_TARGET_DIR']},
    'scratch': str(SCRATCH.relative_to(ROOT)),
    'commands': [],
}

def digest(data):
    return hashlib.sha256(data).hexdigest()

def save():
    RECEIPT_PATH.write_text(json.dumps(receipt, indent=2) + '\n')

def git(path, revision=REVISION):
    return subprocess.check_output(['git', 'show', revision + ':' + path], cwd=ROOT)

def run(name, args, cwd=ROOT, expected=0):
    start = time.monotonic()
    result = subprocess.run(args, cwd=cwd, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log = OUT / (name + '.log')
    # Never overwrite evidence from an earlier failed attempt.
    if log.exists():
        previous = log.read_bytes()
        if previous != result.stdout:
            index = 1
            while (OUT / (name + '.previous-' + str(index) + '.log')).exists():
                index += 1
            log.rename(OUT / (name + '.previous-' + str(index) + '.log'))
    log.write_bytes(result.stdout)
    entry = dict(name=name, argv=list(map(str, args)), cwd=str(cwd), exit_code=result.returncode,
                 expected_exit_code=expected, elapsed_host_seconds=round(time.monotonic() - start, 6),
                 log=str(log.relative_to(ROOT)), log_sha256=digest(result.stdout))
    receipt['commands'].append(entry)
    save()
    print(name + ': exit ' + str(result.returncode), flush=True)
    if result.returncode != expected:
        print(result.stdout.decode(errors='replace')[-14000:], flush=True)
        raise SystemExit(result.returncode or 1)
    return result.stdout.decode(errors='replace')

assert subprocess.run(['git', 'check-ignore', str(SCRATCH.relative_to(ROOT))], cwd=ROOT, stdout=subprocess.DEVNULL).returncode == 0
manifest = git('vm/verification/capability-mailbox/source-manifest.sha256')
assert digest(manifest) == EXPECTED
entries = [line.split('  ', 1) for line in manifest.decode().splitlines()]
assert len(entries) == 47
SOURCE.mkdir(parents=True, exist_ok=True)
for expected, relative in entries:
    data = git(relative)
    assert digest(data) == expected, relative
    target = SOURCE / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        assert target.read_bytes() == data, relative + ' existing snapshot changed'
    else:
        target.write_bytes(data)
    target.chmod(0o444)
(OUT / 'implementation-source-manifest.sha256').write_bytes(manifest)
receipt['implementation_source_digest'] = EXPECTED
receipt['implementation_source_count'] = len(entries)
implementation_receipt = json.loads(git('vm/verification/capability-mailbox/receipt.json'))
receipt['frozen_inputs'] = []
for item in implementation_receipt['frozen_inputs']:
    path = item['path']
    data = git(path)
    previous = git(path, implementation_receipt['base_revision'])
    assert data == previous and digest(data) == item['sha256'], path
    receipt['frozen_inputs'].append(dict(path=path, sha256=digest(data), compared_base_revision=implementation_receipt['base_revision'], equals_base_revision=True))
assert len(receipt['frozen_inputs']) == 12
changed_production = subprocess.check_output(['git', 'diff', implementation_receipt['base_revision'], REVISION, '--', 'vm/Cargo.toml', 'vm/src/lib.rs'], cwd=ROOT)
(OUT / 'feature-wiring.patch').write_bytes(changed_production)
HARNESS.mkdir(parents=True, exist_ok=True)
(HARNESS / 'tests').mkdir(exist_ok=True)
for name in ['adversarial', 'allocator']:
    shutil.copyfile(OUT / (name + '.rs'), HARNESS / 'tests' / (name + '.rs'))
(HARNESS / 'Cargo.toml').write_text('''[package]\nname = "mailbox-independent-review"\nversion = "0.0.0"\nedition = "2021"\n[dependencies]\nmixer-vm = { path = "../source/vm", default-features = false, features = ["experimental-capability-mailbox"] }\n[profile.release]\noverflow-checks = true\npanic = "unwind"\n''')
# A separately derived crate exposes private boundary states only to review tests.
# The immutable original stays unchanged; the production module is a byte prefix.
whitebox = SCRATCH / 'whitebox'
(whitebox / 'src').mkdir(parents=True, exist_ok=True)
original_module = (SOURCE / 'vm/src/experimental_capability/mod.rs').read_bytes()
(whitebox / 'src/lib.rs').write_bytes(original_module + b'\n#[cfg(test)]\nmod independent_review;\n')
shutil.copyfile(SOURCE / 'vm/src/experimental_capability/tests.rs', whitebox / 'src/tests.rs')
shutil.copyfile(OUT / 'whitebox.rs', whitebox / 'src/independent_review.rs')
(whitebox / 'Cargo.toml').write_text('''[package]\nname = "mailbox-boundary-review"\nversion = "0.0.0"\nedition = "2021"\n[profile.release]\noverflow-checks = true\npanic = "unwind"\n''')
receipt['derived_whitebox'] = {'source_prefix': 'vm/src/experimental_capability/mod.rs', 'original_prefix_sha256': digest(original_module), 'derived_source_sha256': digest((whitebox / 'src/lib.rs').read_bytes()), 'change': 'Append only cfg(test) independent_review module declaration; add independently authored review tests; immutable export unchanged'}
review_files = sorted(OUT.glob('*.rs')) + [Path(__file__)]
review_manifest = ''.join(digest(p.read_bytes()) + '  ' + str(p.relative_to(ROOT)) + '\n' for p in review_files)
(OUT / 'review-source-manifest.sha256').write_text(review_manifest)
receipt['review_source_digest'] = digest(review_manifest.encode())
receipt['review_source_manifest'] = str((OUT / 'review-source-manifest.sha256').relative_to(ROOT))
save()
for name, args in [('rustc', ['rustc', '-Vv']), ('cargo', ['cargo', '-V']), ('host', ['uname', '-a']), ('macos', ['sw_vers']), ('python', ['python3', '--version'])]:
    run('version-' + name, args)
run('review-format', ['rustfmt', '--edition', '2021', '--check'] + [str(p) for p in sorted(OUT.glob('*.rs'))])
# Actual negative compilation verifies the default build does not expose the API.
negative = SCRATCH / 'negative-default'
(negative / 'src').mkdir(parents=True, exist_ok=True)
(negative / 'Cargo.toml').write_text('''[package]\nname = "mailbox-default-negative"\nversion = "0.0.0"\nedition = "2021"\n[dependencies]\nmixer-vm = { path = "../source/vm", default-features = false }\n''')
(negative / 'src/main.rs').write_text('use mixer_vm::experimental_capability::Mailbox;\nfn main() { let _ = core::mem::size_of::<Mailbox>(); }\n')
negative_output = run('default-api-negative-compile', ['cargo', 'check', '--manifest-path', str(negative / 'Cargo.toml')], expected=101)
assert 'configured out' in negative_output and 'experimental_capability' in negative_output
# Deliberate compiler/OOM negative probes are expected failures, never clean passes.
for profile in ['debug', 'release']:
    release = [] if profile == 'debug' else ['--release']
    run('independent-' + profile, ['cargo', 'test', '--manifest-path', str(HARNESS / 'Cargo.toml')] + release + ['--', '--nocapture', '--test-threads=1'])
    run('whitebox-' + profile, ['cargo', 'test', '--manifest-path', str(whitebox / 'Cargo.toml')] + release + ['independent_review', '--', '--nocapture', '--test-threads=1'])
run('review-clippy', ['cargo', 'clippy', '--manifest-path', str(HARNESS / 'Cargo.toml'), '--all-targets', '--', '-D', 'warnings'])
run('snapshot-default-execution', ['cargo', 'test', '--locked', '--manifest-path', str(SOURCE / 'vm/Cargo.toml')])
run('snapshot-combined-execution', ['cargo', 'test', '--locked', '--manifest-path', str(SOURCE / 'vm/Cargo.toml'), '--features', 'experimental-capability-mailbox,experimental-stream-validation'])
for expected, relative in entries:
    assert digest((SOURCE / relative).read_bytes()) == expected, relative
assert review_manifest == ''.join(digest(p.read_bytes()) + '  ' + str(p.relative_to(ROOT)) + '\n' for p in review_files)
receipt['immutable_snapshot_unchanged'] = True
receipt['review_sources_unchanged_during_checks'] = True
receipt['completed_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
receipt['result'] = 'Independent host verification passed; read README for findings and limitations'
save()
print('Independent review checks complete', flush=True)
