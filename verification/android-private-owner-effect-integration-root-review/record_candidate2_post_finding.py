"""Retain the observed exact-Work cancellation defect and bounded repair scope."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SOURCE = ROOT / 'verification/android-private-owner-independent-review/implementation-review-1/targeted-5'
def bind(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

result = json.loads((SOURCE / '03-post-failure.stdout').read_bytes())
command = json.loads((SOURCE / '03-post-failure.command.json').read_bytes())
cleanup = json.loads((SOURCE / 'cleanup.json').read_bytes())
assert command['exit_code'] == 1 and result['threwAfterActualEnqueue']
assert result['actualQueuedWorkAfterRetirement'] == 1 and result['actualRemoveCalls'] == 0
assert result['handlerLedger'] == 'RETURNED' and result['samePrimaryFailure']
assert result['actualCorePhase'] == 'RETIRED' and result['JNIcreateCalls'] == 0
assert cleanup['owned_children_reaped'] and cleanup['exclusive_scratch_removed']
assert not cleanup['native_or_capture_started']
files = [SOURCE / name for name in ('03-post-failure.stdout', '03-post-failure.stderr',
    '03-post-failure.command.json', 'cleanup.json', 'compiled-class-hashes.json', 'explicit-sources.list')]
receipt = {
    'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'command': sys.argv, 'python': sys.version, 'script': bind(Path(__file__)),
    'status': 'candidate-2-missed-post-cancellation-and-false-completion-confirmed',
    'candidate_manifest_sha256': 'dc75c6544fdc10d25457c00782dcfb8afbcde756988ce0fd742606bb69c8c0e7',
    'evidence_files': {p.relative_to(ROOT).as_posix(): bind(p) for p in files}, 'result': result,
    'finding': 'post catch clears possibly-enqueued Work before cancelQueued can remove it and reports RETURNED without an attempt.',
    'scope_limit': 'Real core remains retired and later stale delivery is inert; no authority reopening inferred.',
    'selected_repair': 'Retain exact possibly-enqueued Work through actual removal. If terminal reentry occurs during posting, retain the real cleanup token on that Work and defer completion until post unwinds; never remove a newer queued identity.',
    'required_controls': ['before/after enqueue terminal reentry', 'post false and before/after throw or fatal',
        'nested/newer Work identity', 'cleanup reentry', 'failed removal', 'primary/fatal identity and truthful disposition'],
    'new_fixed_Work_fields_require_source_lifetime_review': True,
    'profile_literal_migration_held': True, 'implementation_accepted': False,
    'native_runtime_or_capture_started': False, 'GA_qualified': False,
}
path = OUT / 'candidate-2-post-finding.json'
assert not path.exists()
path.write_text(json.dumps(receipt, indent=2) + '\n')
reference = {'path': path.relative_to(ROOT).as_posix(), **bind(path)}
for filename, key in [('work-graph.json', 'packages'), ('gates/ga.json', 'gates')]:
    p = ROOT / filename
    d = json.loads(p.read_bytes())
    matches = [i['privateOwnerEffectContractCandidate'] for i in d[key] if 'privateOwnerEffectContractCandidate' in i]
    assert len(matches) == 1
    matches[0]['frozen_candidate2']['post_cancellation_finding'] = reference
    p.write_text(json.dumps(d, indent=2) + '\n')
print(json.dumps(reference))
