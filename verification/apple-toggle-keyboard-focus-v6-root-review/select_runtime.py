"""Verify closed host review and select one unchanged setup-only native run."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
bindings = {
    'verification/apple-toggle-keyboard-focus-v6-preparation/packet-seal.json': '5b2743fd61dbabc95abc6e50468347efe406953fb1314785b17013922b6438fd',
    'verification/apple-toggle-keyboard-focus-v6-independent-review/review-seal.json': '24dfa4e5b4b354447fc03686d8b8732c3387ff019f6305f0dd6fc52fb9bcd1c0',
}
counts = {}
for name, digest in bindings.items():
    assert sha(ROOT / name) == digest
    sealed = json.loads((ROOT / name).read_text())['files']
    for path, expected in sealed.items():
        p = ROOT / path
        assert p.is_file() and not p.is_symlink() and sha(p) == expected, path
    counts[name] = len(sealed)
review = json.loads((ROOT / 'verification/apple-toggle-keyboard-focus-v6-independent-review/review.json').read_text())
assert review['findings'] == [] and review['freshIndependentMethodsPassed'] == 10
assert review['frozenV5StaleJournal']['v6Rejected'] and review['producerSealedFilesVerifiedBeforeAndAfter'] == 184
assert review['independentlyRerunExistingPythonMethodsPassed'] == 269
preflight = json.loads((OUT / 'preflight.stdout').read_text())
assert preflight['sealSHA256'] == bindings['verification/apple-toggle-keyboard-focus-v6-preparation/packet-seal.json']
assert preflight['expectedXCTestMethods'] == 1 and not preflight['nativeExecution']
for name in ['select_runtime.py', 'preflight.stdout', 'preflight-command.json']:
    bindings[str((OUT / name).relative_to(ROOT))] = sha(OUT / name)
command = ['python3', '-B', 'verification/apple-toggle-keyboard-focus-v6-preparation/run.py', 'run', '--scope', 'interaction', '--reviewed-seal', preflight['sealSHA256']]
selection = {
    'schema': 'mixer.apple-toggle.keyboard-v6-root-runtime-selection.1',
    'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'accountableReviewer': '/root',
    'sourceRevisionContext': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'tool': {'path': str(Path(sys.executable).resolve()), 'version': sys.version, 'sha256': sha(Path(sys.executable).resolve())},
    'bindings': bindings, 'sealedFilesVerified': counts,
    'selectedRuntimeCommand': command,
    'scope': 'One setup-only public Settings XCTest diagnostic. Exact reviewed host ordering repair; app, native runner, oracle, transport and bounds unchanged. Six app keyboard cases remain unrun even if setup succeeds.',
    'qualification': 'DIAGNOSTIC_ONLY; inherited strict native assertion stays false. Distinguish expected diagnostic boundary from actual XCTest/setup failure.',
    'instancePolicy': 'One owned disposable iOS26.5 simulator; preserve unrelated instances/frontend and perform independent all-outcome cleanup.',
    'nativeRuntimeSelected': True, 'nativeRuntimeAccepted': False,
    'liveIntegrationSelected': False, 'physicalPhones': 'disconnected-deferred', 'gaAccepted': False,
}
destination = OUT / 'selection.json'
assert not destination.exists(), 'Selection already recorded; do not silently repeat a native attempt'
destination.write_text(json.dumps(selection, indent=2) + '\n')
print(json.dumps({'selectionSHA256': sha(destination), 'verifiedFiles': counts, 'command': command}))
