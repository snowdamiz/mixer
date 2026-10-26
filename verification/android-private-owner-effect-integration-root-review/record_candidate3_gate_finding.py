"""Bind the independent dirty-completion witness and hold stale CLI integration."""
import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
REVIEW = ROOT / 'verification/android-private-owner-independent-review/implementation-review-2'
WITNESS = REVIEW / 'targeted-6'

def bind(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

seal_path = WITNESS / 'witness-seal.json'
assert bind(seal_path)['sha256'] == 'f0bf0150fed64e0e3b47da17e7432ffa1d32d1ae34f2c678b478fc6429e9f1e2'
seal = json.loads(seal_path.read_bytes())
members = seal['files'] if 'files' in seal else seal['members']
for name, expected in members.items():
    parts = PurePosixPath(name)
    assert not parts.is_absolute() and '..' not in parts.parts
    path = REVIEW
    for part in parts.parts:
        path /= part
        assert not path.is_symlink()
    assert bind(path) == expected, name
assert len(members) == 128 and sum(m['bytes'] for m in members.values()) == 1396374
result = json.loads((WITNESS / '03-active-lifecycle-dirty.stdout').read_bytes())
command = json.loads((WITNESS / '03-active-lifecycle-dirty.command.json').read_bytes())
cleanup = json.loads((WITNESS / 'cleanup.json').read_bytes())
assert command['exit_code'] == 1 and result['lifecycleDirtyDuringActualPrepare']
assert result['actualCurrentGateOpenAtPost'] and not result['sharedAuthorityOpenAtPost']
assert result['actualCorePhase'] == 'LIVE' and result['actualCoreDirty']
assert result['actualQueuedDrains'] == 1 and result['JNIcommitCalls'] == 1
assert result['inputCancellationReturnedWhileCoordinatorBusy']
assert cleanup['owned_children_reaped'] and cleanup['exclusive_scratch_removed']
assert not cleanup['native_or_capture_started']
selection = OUT / 'candidate-3-profile-selection.json'
assert bind(selection)['sha256'] == 'bc6ffacdd63674ba1c6d3a5bbf8c86f965e191d22113056157c116255e73b542'
receipt = {
    'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'command': sys.argv, 'python': sys.version, 'script': bind(Path(__file__)),
    'context_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'status': 'candidate-3-concrete-gate-dirty-completion-failure-confirmed-CLI-held',
    'candidate_manifest_sha256': seal['candidate_manifest_sha256'],
    'witness_seal': {'path': seal_path.relative_to(ROOT).as_posix(), **bind(seal_path)},
    'witness_members_verified': len(members), 'witness_bytes_verified': 1396374,
    'result': result,
    'scope_limit': 'Concrete gate closure violated; shared draw/input permissions remained false. No native runtime or released product qualification.',
    'supersedes_profile_selection': {'path': selection.relative_to(ROOT).as_posix(), **bind(selection)},
    'CLI_state': 'Four root-owned source/test edits contain candidate-3 profile hashes. No CLI build/tests or delivery started; rebind only after corrected candidate freeze and root selection.',
    'selected_repair': 'Retain successful lifecycle-dirty commit/finish/core.complete(committed=true). Scalar-close current/pending concrete gates before completion bookkeeping hooks or later post callbacks; publish only for clean current core completion, outside the commit-to-finish interval.',
    'required_controls': ['lifecycle-only dirty completion and one drain', 'completionFault boundary', 'clean current successor publication', 'observer-stale abort remains distinct', 'no callback/capture/allocation added to commit-to-finish interval'],
    'profile_literal_validation_or_delivery_authorized': False,
    'implementation_accepted': False, 'native_runtime_or_capture_started': False, 'GA_qualified': False,
}
path = OUT / 'candidate-3-gate-finding-and-hold.json'
assert not path.exists()
path.write_text(json.dumps(receipt, indent=2) + '\n')
reference = {'path': path.relative_to(ROOT).as_posix(), **bind(path)}
for filename, key in [('work-graph.json', 'packages'), ('gates/ga.json', 'gates')]:
    p = ROOT / filename
    data = json.loads(p.read_bytes())
    rows = [x['privateOwnerEffectContractCandidate'] for x in data[key] if 'privateOwnerEffectContractCandidate' in x]
    assert len(rows) == 1
    row = rows[0]
    row['implementation_status'] = 'candidate3-independent-concrete-gate-failure-candidate4-repair-active-CLI-held'
    row['frozen_candidate3']['independent_review'] = 'Rejected for concrete gate reopening at lifecycle-dirty completion; targeted prior repairs and additional controls pass, complete matrix pending.'
    row['frozen_candidate3']['gate_finding_and_CLI_hold'] = reference
    row['frozen_candidate3']['profile_literal_migration_authorized'] = False
    p.write_text(json.dumps(data, indent=2) + '\n')
print(json.dumps(reference))
