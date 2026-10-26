"""Bind observed candidate-2 review findings without promoting implementation."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
CANDIDATE = ROOT / 'verification/android-private-owner-integration-implementation/candidate-2'
OBSERVED = ROOT / 'verification/android-private-owner-independent-review/implementation-review-1/targeted-3'

def bind(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

assert bind(CANDIDATE / 'manifest.json')['sha256'] == 'dc75c6544fdc10d25457c00782dcfb8afbcde756988ce0fd742606bb69c8c0e7'
result = json.loads((OBSERVED / '03-terminal.stdout').read_bytes())
command = json.loads((OBSERVED / '03-terminal.command.json').read_bytes())
cleanup = json.loads((OBSERVED / 'cleanup.json').read_bytes())
assert command['exit_code'] == 1 and result['actualCancellationReentry']
assert result['actualCorePhase'] == 'RETIRED'
assert not result['drawAllowed'] and not result['inputAllowed']
assert result['JNIprepareCalls'] == result['JNIdestroyCalls'] == 1
assert cleanup['owned_children_reaped'] and cleanup['exclusive_scratch_removed']
assert not cleanup['native_or_capture_started']
correction = ROOT / 'docs/android-private-owner-effect-integration-correction.md'
text = correction.read_text()
assert 'Add the explicit scope parameter to `Record` construction, `Record.bind`' in text
assert 'recursive helpers pass the same scope, never recapture' in text
files = [OBSERVED / x for x in ('03-terminal.stdout', '03-terminal.stderr', '03-terminal.command.json',
    'cleanup.json', 'compiled-class-hashes.json', 'explicit-sources.list')]
files += [correction, CANDIDATE / 'source/native/android/app/src/dev/mixer/android/NativeAppearanceViewsV2.java',
    CANDIDATE / 'source/native/android/tests/NativeAppearanceV2Instrumentation.java', Path(__file__).resolve()]
receipt = {
    'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'python': sys.version, 'argv': sys.argv,
    'context_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'candidate_manifest_sha256': bind(CANDIDATE / 'manifest.json')['sha256'],
    'status': 'candidate-2-additional-repairs-selected-implementation-unaccepted',
    'evidence_files': {p.relative_to(ROOT).as_posix(): bind(p) for p in files},
    'terminal_result': result,
    'findings': [
        {'id': 'terminal-readiness-continuation', 'evidence': 'independent actual-source Java host execution',
         'finding': 'Cancellation reentry closes the real owner but onResume continues ordinary readiness probes.',
         'limit': 'Core stays retired and gates closed; no authority reopening or additional prepare is observed.',
         'selected_repair': 'Stop start/onResume/drain ordinary focus/window probes after terminal seal reentry.'},
        {'id': 'explicit-mutation-propagation', 'evidence': 'frozen source review and explicit selected C3 contract',
         'finding': 'Seven helpers rediscover mutation instead of receiving the explicitly required captured argument.',
         'limit': 'No reproduced successor-token bypass; current transaction rediscovery uses the same retained scope.',
         'selected_repair': 'Pass existing Mutation through Record construction/bind/measure/measureList/installChildren/layoutRoot/layout and recursive/live callers.'},
        {'id': 'private-fixture-acquisition-unwind', 'evidence': 'frozen private fixture source review only',
         'finding': 'Failure after observer registration and before fixture tracking leaves acquired ownership without a returned handle.',
         'selected_repair': 'Unwind partial observer/renderer/core acquisition and separately attached dedicated root on factory failure, preserving original/fatal failures.'}
    ],
    'producer_corrections_authorized': True, 'profile_literal_migration_held': True,
    'implementation_accepted': False, 'native_runtime_or_capture_started': False, 'GA_qualified': False
}
path = OUT / 'candidate-2-followup-findings.json'
assert not path.exists()
path.write_text(json.dumps(receipt, indent=2) + '\n')
reference = {'path': path.relative_to(ROOT).as_posix(), **bind(path), 'status': receipt['status']}
for filename, key in [('work-graph.json', 'packages'), ('gates/ga.json', 'gates')]:
    metadata_path = ROOT / filename
    data = json.loads(metadata_path.read_bytes())
    items = [item['privateOwnerEffectContractCandidate'] for item in data[key] if 'privateOwnerEffectContractCandidate' in item]
    assert len(items) == 1
    item = items[0]
    item['frozen_candidate2']['additional_followup_findings'] = reference
    item['implementation_status'] = 'candidate2-custody-verified-ledger-focus-scope-and-cleanup-repairs-active-independent-review-in-progress'
    metadata_path.write_text(json.dumps(data, indent=2) + '\n')
print(json.dumps(reference))
