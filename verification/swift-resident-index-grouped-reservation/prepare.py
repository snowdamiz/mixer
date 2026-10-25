#!/usr/bin/env python3
"""Select a sealed clean storage derivative; do not change the live VM."""
from pathlib import Path
import datetime
import difflib
import hashlib
import json
import shutil
import subprocess
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
INPUT = ROOT / 'verification/swift-index-ticket-storage-diagnosis'
TOOLS = Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin')

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()

def save(name, value):
    (OUT / name).write_bytes(encoded(value))

assert not (OUT / 'selection.json').exists()
assert sha(INPUT / 'seal.json') == '44e3aeedcbca786326a565683929ffb1a4e30428898356b50633985ce9f1812d'
verify = subprocess.run([sys.executable, '-B', str(INPUT / 'verify.py')], capture_output=True, timeout=60)
(OUT / 'input-verify.stdout').write_bytes(verify.stdout)
(OUT / 'input-verify.stderr').write_bytes(verify.stderr)
assert verify.returncode == 0
baseline = json.loads((INPUT / 'input-source-manifest.json').read_bytes())
clean = json.loads((INPUT / 'implementation-source-manifest.json').read_bytes())
assert len(baseline) == len(clean) == 132
assert {n: sha(ROOT / 'vm' / n) for n in baseline} == baseline
source = OUT / 'source'
assert not source.exists()
for name, digest in clean.items():
    old = INPUT / 'implementation-source' / name
    assert sha(old) == digest
    dest = source / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(old, dest)
cache = source / 'src/experimental_swift_reactor/cache.rs'
before = cache.read_text()
old = '    let Some(header) = exclusive.checked_add(cleanup) else { return None; };'
new = '    let Some(header) = exclusive.checked_add(cleanup) else {\n        return None;\n    };'
assert before.count(old) == 1
cache.write_text(before.replace(old, new))
(OUT / 'format-only.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True), cache.read_text().splitlines(True), fromfile='diagnosis/cache.rs', tofile='selected/cache.rs')))
argv = [str(TOOLS / 'rustfmt'), '--edition', '2021', '--config', 'skip_children=true', '--check', str(cache), str(source / 'src/experimental_swift_reactor/cache_tests.rs')]
fmt = subprocess.run(argv, capture_output=True, timeout=30)
(OUT / 'format.stdout').write_bytes(fmt.stdout)
(OUT / 'format.stderr').write_bytes(fmt.stderr)
assert fmt.returncode == 0
selected = {n: sha(source / n) for n in clean}
changed = [n for n in selected if selected[n] != baseline[n]]
assert sorted(changed) == ['src/experimental_swift_reactor/cache.rs', 'src/experimental_swift_reactor/cache_tests.rs']
assert [n for n in selected if selected[n] != clean[n]] == ['src/experimental_swift_reactor/cache.rs']
save('source-manifest.json', selected)
save('baseline-manifest.json', baseline)
save('selection.json', {
    'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'sourceRevision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'diagnosisSealSHA256': sha(INPUT / 'seal.json'), 'diagnosisReceiptSHA256': sha(INPUT / 'receipt.json'),
    'contractSHA256': sha(ROOT / 'docs/swift-resident-index-grouped-reservation-contract.md'),
    'sourceDigest': hashlib.sha256(encoded(selected)).hexdigest(), 'sourceManifestSHA256': sha(OUT / 'source-manifest.json'),
    'cleanInputSHA256': sha(INPUT / 'implementation-source-manifest.json'),
    'changedFiles': changed, 'inputVerification': json.loads(verify.stdout),
    'formatOnlyPatchSHA256': sha(OUT / 'format-only.patch'),
    'formatCheck': {'argv': argv, 'exitCode': fmt.returncode, 'stdoutSHA256': sha(OUT / 'format.stdout'), 'stderrSHA256': sha(OUT / 'format.stderr'), 'rustfmtSHA256': sha(TOOLS / 'rustfmt'), 'version': subprocess.check_output([str(TOOLS / 'rustfmt'), '--version'], text=True).strip()},
    'isolatedImplementationSelected': True, 'liveIntegrated': False, 'fullTargetSelected': False,
    'nativeExecuted': False, 'gaAccepted': False,
})
print(json.dumps({'sourceDigest': hashlib.sha256(encoded(selected)).hexdigest(), 'changedFiles': changed, 'isolatedOnly': True}))
