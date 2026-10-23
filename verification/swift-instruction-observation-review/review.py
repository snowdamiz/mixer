#!/usr/bin/env python3
"""Independent frozen-revision review. Never invokes/reseals producer scripts."""
import hashlib
import io
import json
import os
import platform
import re
import subprocess
import tarfile
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REV = '3a1bb5a455973bde841a4b57993277fa2c054569'
BASE = '45852204fbcced037d8e530876b619d9ed1c2ce1'
sha = lambda data: hashlib.sha256(data).hexdigest()
read = lambda path: json.loads(path.read_text())
def entries(raw):
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        return {m.name: sha(archive.extractfile(m).read()) for m in archive.getmembers() if m.isfile()}
def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)

producer = ROOT / 'verification/swift-instruction-observation'
receipt_raw = (producer / 'isolated-1/receipt.json').read_bytes()
receipt = json.loads(receipt_raw)
root_raw = (producer / 'root-audit.json').read_bytes()
root = json.loads(root_raw)
assert receipt['base_revision'] == BASE and receipt['passed'] and root['passed']
assert sha(receipt_raw) == root['receipt_sha256']
assert sha((producer / 'collect.py').read_bytes()) == receipt['collector_sha256']
assert sha((producer / 'audit.py').read_bytes()) == root['auditor_sha256']
candidate_raw = git('archive', REV, 'vm')
candidate = entries(candidate_raw)
baseline = entries(git('archive', BASE, 'vm'))
assert set(candidate) == set(baseline)
changed = {k: candidate[k] for k in candidate if candidate[k] != baseline[k]}
assert set(changed) == set(receipt['overlays']) == {
    'vm/src/experimental_swift_reactor/control.rs',
    'vm/src/experimental_swift_reactor/control_tests.rs',
}
assert changed == root['source_overlays']
archive = ROOT / receipt['source_archive']
assert sha(archive.read_bytes()) == receipt['source_archive_sha256']
assert entries(archive.read_bytes()) == receipt['source_files'] == candidate
tree_digest = sha(json.dumps(candidate, sort_keys=True).encode())
assert tree_digest == receipt['source_tree_sha256'] == root['source_tree_sha256']
bindings = len(candidate) * 2 + len(changed) + 3
counts = {}
preserved = {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in [producer/'isolated-1/receipt.json', producer/'root-audit.json', producer/'collect.py', producer/'audit.py', archive]}
for cmd in receipt['commands']:
    data = (ROOT / cmd['log']).read_bytes()
    assert sha(data) == cmd['sha256'] and cmd['exit'] == 0 and cmd['source_stable']
    preserved[cmd['log']] = sha(data)
    bindings += 1
    label = cmd['label']
    if label in ('debug','release','debug-oracles','release-oracles','debug-minimal-swift','release-minimal-swift'):
        totals = re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored', data.decode())
        assert totals and all(int(t[1]) == 0 for t in totals)
        count = sum(int(t[0]) for t in totals)
        assert count == (9 if 'oracles' in label else 72 if 'minimal' in label else 319)
        counts[label] = count
        if 'oracles' not in label:
            assert b'test experimental_swift_reactor::control::tests::instruction_and_bulk_fuel_failures_retain_actual_wasi_counters ... ok' in data
            bindings += 1
assert bindings == root['verified_bindings'] == 853

(HERE/'source.tar').write_bytes(candidate_raw)
(HERE/'source-manifest.json').write_text(json.dumps(candidate, indent=2, sort_keys=True)+'\n')
build = HERE / '.build'
source = build / 'source'
source.mkdir(parents=True, exist_ok=True)
with tarfile.open(fileobj=io.BytesIO(candidate_raw)) as tar:
    tar.extractall(source, filter='data')
env = dict(os.environ)
env['PATH'] = '/opt/homebrew/opt/rustup/bin:' + env['PATH']
env['CARGO_TARGET_DIR'] = str(build/'target')
commands = []
def run(label, argv, expected=None):
    start = time.monotonic()
    proc = subprocess.run(argv, cwd=source, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    data = proc.stdout
    (HERE/(label+'.log')).write_bytes(data)
    item = {'label': label, 'argv': argv, 'cwd': str(source), 'exit': proc.returncode,
            'seconds': time.monotonic()-start, 'log': str((HERE/(label+'.log')).relative_to(ROOT)), 'sha256': sha(data)}
    if expected is not None:
        totals = re.findall(r'test result: ok\. (\d+) passed; (\d+) failed;', data.decode())
        item['passed_tests'] = sum(int(t[0]) for t in totals)
        assert totals and item['passed_tests'] == expected and all(int(t[1])==0 for t in totals), data.decode()
    commands.append(item)
    assert proc.returncode == 0, data.decode()
    print(label, 'passed', flush=True)
run('rust-version', ['rustc','--version','--verbose'])
run('cargo-version', ['cargo','--version','--verbose'])
base_command = ['cargo','test','--locked','--manifest-path','vm/Cargo.toml','--features','experimental-swift-reactor','--lib']
fixture = 'experimental_swift_reactor::control::tests::instruction_and_bulk_fuel_failures_retain_actual_wasi_counters'
for mode in ['debug','release']:
    run(mode+'-actual-eleven',base_command+(['--release'] if mode=='release' else [])+[fixture,'--','--exact','--nocapture'],1)
snapshot_tests = source/'vm/src/experimental_swift_reactor/control_tests.rs'
snapshot_tests.write_bytes(snapshot_tests.read_bytes()+(HERE/'boundary_probes.rs').read_bytes())
probe_manifest = {str(p.relative_to(source)): sha(p.read_bytes()) for p in source.rglob('*') if p.is_file() and 'target' not in p.parts}
probe_digest = sha(json.dumps(probe_manifest,sort_keys=True).encode())
for mode in ['debug','release']:
    run(mode+'-independent-boundaries',base_command+(['--release'] if mode=='release' else [])+['experimental_swift_reactor::control::tests::review_','--','--nocapture'],3)
assert {str(p.relative_to(source)): sha(p.read_bytes()) for p in source.rglob('*') if p.is_file() and 'target' not in p.parts} == probe_manifest
assert all(sha((ROOT/p).read_bytes())==digest for p,digest in preserved.items())
result = {
    'completed_utc': datetime.now(timezone.utc).isoformat(), 'reviewer': '/root/swift_executor_prerequisite_review',
    'model': 'gpt-6.1-sol', 'reasoning_effort': 'xhigh', 'python': platform.python_version(),
    'revision': REV, 'base_revision': BASE, 'source_archive': str((HERE/'source.tar').relative_to(ROOT)),
    'source_archive_sha256': sha(candidate_raw), 'source_tree_sha256': tree_digest,
    'source_files': len(candidate), 'changed_sources': changed, 'producer_receipt_sha256': sha(receipt_raw),
    'root_audit_sha256': sha(root_raw), 'audited_bindings': bindings, 'audited_test_counts': counts,
    'probe_sha256': sha((HERE/'boundary_probes.rs').read_bytes()), 'probe_tree_sha256': probe_digest,
    'script_sha256': sha(Path(__file__).read_bytes()), 'commands': commands,
    'preserved_artifacts': preserved, 'producer_artifacts_unchanged': True, 'passed': True,
    'probe_authoring_note': 'Initial None-parity probe compared historical validation wall-clock durations across separately validated fixtures; the retained probe-authoring-failure.log records this harness-only failure. Final comparison normalizes only runtime and historical validation elapsed/overshoot fields.',
    'decision': 'accepted-private-instruction-observation-prerequisite',
    'scope': 'Frozen two-file private control delta only; actual WASI observation, unchanged None behavior/arithmetic/order/layout; independent host control probes. No executor/cache acceptance, target instantiation/execution, compiler/device/signing/store/dogfood or GA qualification.'
}
(HERE/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed': True, 'audited_bindings':bindings, 'receipt_sha256':sha((HERE/'receipt.json').read_bytes())}),flush=True)
